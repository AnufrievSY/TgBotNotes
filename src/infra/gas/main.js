/**
 * WebApp endpoint: POST JSON
 *
 * actions:
 *  - upsert_note: create/update row by id (message_id)
 *  - add_track: append one/many track links to playlist cell (new line, rich links)
 *  - exists: check row exists by id
 *
 * Data model (columns):
 * 1 id
 * 2 Когда (dd.mm.YYYY HH:MM:SS)
 * 3 Что
 * 4 Эмоции (через ", ")
 * 5 Теги (через ", ")
 * 6 Плейлист (rich text, each line clickable)
 */

const SPREADSHEET_BY_USER = {
  // "AnotherUser": "spreadsheetId..."
};

const SHEET_NAME = "Лист1";
const HEADERS = ["id", "Когда", "Что", "Эмоции", "Теги", "Плейлист"];

function doPost(e) {
  try {
    const payload = JSON.parse((e && e.postData && e.postData.contents) || "{}");
    const action = payload.action;
    const user = payload.user;

    if (!user) return json_({ ok: false, error: "user is required" });

    const ssId = SPREADSHEET_BY_USER[user];
    if (!ssId) return json_({ ok: false, error: `Unknown user: ${user}` });

    const ss = SpreadsheetApp.openById(ssId);
    const sheet = getOrCreateSheet_(ss, SHEET_NAME);
    ensureHeader_(sheet);

    if (action === "exists") {
      const id = String(payload.id || "");
      if (!id) return json_({ ok: false, error: "id required" });

      const row = findRowById_(sheet, id);
      return json_({ ok: true, exists: row !== 0 });
    }

    if (action === "upsert_note") {
      const rec = payload.record || {};
      const id = String(rec.id || "");
      if (!id) return json_({ ok: false, error: "record.id required" });

      const row = findRowById_(sheet, id);

      const whenStr = String(rec.when || formatDateTime_(new Date()));
      const what = String(rec.what || "");
      const emotions = Array.isArray(rec.emotions) ? rec.emotions : [];
      const tags = Array.isArray(rec.tags) ? rec.tags : [];

      const values = [
        id,
        whenStr,
        what,
        emotions.join(", "),
        tags.join(", "),
        "" // playlist untouched here
      ];

      if (row === 0) {
        sheet.appendRow(values);
      } else {
        // update A-E only; keep playlist (F) as is
        sheet.getRange(row, 1, 1, 5).setValues([values.slice(0, 5)]);
      }

      return json_({ ok: true });
    }

    if (action === "add_track") {
      const id = String(payload.id || "");
      if (!id) return json_({ ok: false, error: "id required" });

      const row = findRowById_(sheet, id);
      if (row === 0) return json_({ ok: false, error: `Row with id=${id} not found` });

      // accept items: [{link, text}]
      let items = [];
      if (Array.isArray(payload.items)) items = payload.items;

      // если вдруг прилетела одна штука (на будущее)
      if (!Array.isArray(items) || items.length === 0) {
        return json_({ ok: false, error: "items[] required" });
      }

      // чистим вход
      items = items
        .map(it => ({
          link: String((it && it.link) || "").trim(),
          text: String((it && it.text) || "").trim(),
        }))
        .filter(it => it.link && it.text);

      if (items.length === 0) {
        return json_({ ok: false, error: "items[] must contain {link,text}" });
      }

      const cell = sheet.getRange(row, 6); // F column
      const added = appendItemsToCell_(cell, items);

      return json_({ ok: true, added: added });
    }

    return json_({ ok: false, error: `Unknown action: ${action}` });
  } catch (err) {
    return json_({
      ok: false,
      error: String(err),
      stack: (err && err.stack) ? String(err.stack) : ""
    });
  }
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function getOrCreateSheet_(ss, name) {
  let sheet = ss.getSheetByName(name);
  if (!sheet) sheet = ss.insertSheet(name);
  return sheet;
}

function ensureHeader_(sheet) {
  const firstRow = sheet.getRange(1, 1, 1, HEADERS.length).getValues()[0];
  const ok = HEADERS.every((h, i) => String(firstRow[i] || "").trim() === h);
  if (!ok) {
    sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
    sheet.setFrozenRows(1);
  }
}

function findRowById_(sheet, id) {
  const last = sheet.getLastRow();
  if (last < 2) return 0;

  const values = sheet.getRange(2, 1, last - 1, 1).getValues();
  for (let i = 0; i < values.length; i++) {
    if (String(values[i][0]) === id) return i + 2;
  }
  return 0;
}

function formatDateTime_(d) {
  const pad = (n) => String(n).padStart(2, "0");
  const dd = pad(d.getDate());
  const mm = pad(d.getMonth() + 1);
  const yyyy = d.getFullYear();
  const hh = pad(d.getHours());
  const mi = pad(d.getMinutes());
  const ss = pad(d.getSeconds());
  return `${dd}.${mm}.${yyyy} ${hh}:${mi}:${ss}`;
}

function appendItemsToCell_(cell, items) {
  // 1) читаем старый rich text, чтобы не потерять ссылки
  const rich = cell.getRichTextValue();
  const oldText = rich ? String(rich.getText() || "") : String(cell.getDisplayValue() || "");
  const oldLines = oldText ? oldText.split("\n") : [];

  // 2) восстановим map: lineText -> linkUrl из старого rich
  // (если строка повторяется, возьмем первую встретившуюся ссылку)
  const linkByText = {}; // text -> url
  if (rich && oldText) {
    let pos = 0;
    for (let i = 0; i < oldLines.length; i++) {
      const line = String(oldLines[i] || "");
      const lineLen = line.length;

      // ссылка в рамках этой строки: возьмём ссылку первого символа строки
      // (у нас весь line обычно под одной ссылкой)
      if (lineLen > 0) {
        const url = rich.getLinkUrl(pos, pos + 1);
        if (url && !linkByText[line]) linkByText[line] = url;
      }

      pos += lineLen + 1; // + '\n'
    }
  }

  // 3) добавляем новые элементы (антидубль по text)
  const lines = oldLines.filter(s => String(s).trim() !== "");
  const seen = new Set(lines);

  let added = 0;
  for (let i = 0; i < items.length; i++) {
    const link = String((items[i] && items[i].link) || "").trim();
    const text = String((items[i] && items[i].text) || "").trim();
    if (!link || !text) continue;

    if (seen.has(text)) continue;
    seen.add(text);

    lines.push(text);
    linkByText[text] = link;
    added += 1;
  }

  // 4) собираем новый rich text и проставляем ссылки для ВСЕХ строк
  const newText = lines.join("\n");
  const builder = SpreadsheetApp.newRichTextValue().setText(newText);

  let pos = 0;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const start = pos;
    const end = pos + line.length;

    const url = linkByText[line];
    if (url && line.length > 0) {
      builder.setLinkUrl(start, end, url);
    }

    pos = end + 1;
  }

  cell.setRichTextValue(builder.build());
  cell.setWrap(true);

  return added;
}
