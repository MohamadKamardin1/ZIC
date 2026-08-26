const SMALL_NUMBERS = [
  "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
  "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
]
const TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
const SCALES = ["", "thousand", "million", "billion", "trillion"]

function underThousand(value: number): string {
  const words: string[] = []
  const hundreds = Math.floor(value / 100)
  const remainder = value % 100
  if (hundreds > 0) words.push(`${SMALL_NUMBERS[hundreds]} hundred`)
  if (remainder > 0) {
    if (remainder < 20) words.push(SMALL_NUMBERS[remainder])
    else {
      const tens = Math.floor(remainder / 10)
      const units = remainder % 10
      words.push(units ? `${TENS[tens]}-${SMALL_NUMBERS[units]}` : TENS[tens])
    }
  }
  return words.join(" ")
}

function integerToWords(value: number): string {
  if (value === 0) return "zero"
  const parts: string[] = []
  let remainder = Math.floor(value)
  let scale = 0
  while (remainder > 0) {
    const group = remainder % 1000
    if (group > 0) parts.unshift(`${underThousand(group)}${SCALES[scale] ? ` ${SCALES[scale]}` : ""}`)
    remainder = Math.floor(remainder / 1000)
    scale += 1
  }
  return parts.join(" ")
}

function currencyName(label: string, code: string): string {
  const parts = label.split(/\s*[—-]\s*/)
  const name = parts.length > 1 ? parts.slice(1).join(" — ").trim() : ""
  if (name) return name.toLowerCase()
  if (code.toUpperCase() === "TZS") return "Tanzanian shillings"
  if (code.toUpperCase() === "USD") return "US dollars"
  return code ? `${code.toUpperCase()} currency units` : "currency units"
}

function pluralizeCurrency(name: string, amount: number): string {
  if (amount === 1 || name.endsWith("s")) return name
  if (name.endsWith("y")) return `${name.slice(0, -1)}ies`
  return `${name}s`
}

export function amountToWords(rawAmount: string, currencyCode = "", currencyLabel = ""): string {
  const amount = Number(rawAmount)
  if (!Number.isFinite(amount) || amount <= 0) return "Enter an amount to preview it in words."
  const rounded = Math.round((amount + Number.EPSILON) * 100) / 100
  const whole = Math.floor(rounded)
  const minor = Math.round((rounded - whole) * 100)
  const majorWords = integerToWords(whole)
  const majorCurrency = pluralizeCurrency(currencyName(currencyLabel, currencyCode), whole).replace(/^./, (character) => character.toUpperCase())
  const minorWords = minor > 0 ? ` and ${integerToWords(minor)} cents` : ""
  return `${majorWords} ${majorCurrency}${minorWords} only`.replace(/^./, (character) => character.toUpperCase())
}
