/** Minimal RFC-4180-lite CSV parsing shared by import flows and templates. */

function parseCsvLine(line: string): string[] {
  const result: string[] = []
  let current = ""
  let quoted = false
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index]
    if (character === '"' && line[index + 1] === '"' && quoted) {
      current += '"'
      index += 1
    } else if (character === '"') {
      quoted = !quoted
    } else if (character === "," && !quoted) {
      result.push(current.trim())
      current = ""
    } else {
      current += character
    }
  }
  result.push(current.trim())
  return result
}

export function parseCsv(text: string): Array<Record<string, string>> {
  const lines = text.split(/\r?\n/).filter((line) => line.trim())
  if (lines.length < 2) return []
  const headers = parseCsvLine(lines[0]).map((header) => header.toLowerCase())
  return lines.slice(1).map((line) => Object.fromEntries(parseCsvLine(line).map((value, index) => [headers[index], value])))
}

export function toCsv(rows: Array<Record<string, string>>): string {
  if (rows.length === 0) return ""
  const headers = Object.keys(rows[0])
  const escape = (value: string) => `"${String(value ?? "").split('"').join('""')}"`
  return [
    headers.map(escape).join(","),
    ...rows.map((row) => headers.map((header) => escape(row[header] ?? "")).join(",")),
  ].join("\n")
}