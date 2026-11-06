import { Table2 } from 'lucide-react'
import { formatMoney, isMoneyColumn } from '../utils/formatMoney'

function display(value, isMoney = false) {
  if (value === null || value === undefined || value === '') return '—'
  if (isMoney) return formatMoney(value)
  return String(value)
}

function DataTable({ dataset }) {
  if (!dataset) return <div className="empty-state"><span><Table2 size={23} /></span><h3>Your data preview will appear here</h3><p>Upload a CSV or Excel file to review its rows and columns.</p></div>
  const amountColumn = dataset.analysis.detected_columns.amount

  return (
    <div className="table-card">
      <div className="table-card-heading"><div><h3>Dataset preview</h3><p>{dataset.columns.length} columns · {dataset.row_count.toLocaleString()} rows</p></div><span className="preview-limit">Showing first {Math.min(dataset.preview.length, 100)} rows</span></div>
      <div className="table-scroll" role="region" aria-label="Dataset preview table" tabIndex="0">
        <table>
          <thead><tr><th className="row-index">#</th>{dataset.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>{dataset.preview.map((row, index) => <tr key={`${index}-${dataset.dataset_id}`}><td className="row-index">{index + 1}</td>{dataset.columns.map((column) => { const formatted = display(row[column], isMoneyColumn(column) || column === amountColumn); return <td key={column} title={formatted}>{formatted}</td> })}</tr>)}</tbody>
        </table>
      </div>
      {dataset.row_count > dataset.preview.length && <div className="table-card-footer">Preview is limited to 100 rows to keep the dashboard responsive.</div>}
    </div>
  )
}

export default DataTable
