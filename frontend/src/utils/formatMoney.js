const inrFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function formatMoney(value) {
  if (value === null || value === undefined || value === '') return '—'
  const numeric = typeof value === 'number'
    ? value
    : Number(String(value).replace(/[₹$£€,\s]/g, ''))
  return Number.isFinite(numeric) ? inrFormatter.format(numeric) : String(value)
}

export function isMoneyColumn(columnName) {
  const normalized = String(columnName)
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/[()]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  if (/\b(method|category|type|count|number|id)\b/.test(normalized)) return false
  return /\b(amount|income|expenses?|revenue|balance|debit|credit|cash flow|price|cost|salary|refund)\b/.test(normalized)
}
