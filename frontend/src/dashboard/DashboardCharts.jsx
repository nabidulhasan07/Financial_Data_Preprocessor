import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatMoney } from '../utils/formatMoney'

function DashboardCharts({ analysis }) {
  const categoryData = analysis.category_summary ?? []
  const monthly = analysis.monthly_summary ?? []
  const mix = [
    { name: 'Income', value: analysis.total_income },
    { name: 'Expenses', value: analysis.total_expenses },
  ].filter((item) => item.value > 0)

  return (
    <div className="analysis-grid">
      <article className="dash-card chart-card"><div className="dash-card-heading"><div><h3>Income and expenses</h3><p>Monthly totals from recognized dates and amounts</p></div></div>
        {monthly.length ? <div className="analysis-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={monthly} margin={{ top: 12, right: 6, left: 4, bottom: 0 }}><CartesianGrid vertical={false} stroke="#edf2f7" strokeDasharray="3 5" /><XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#8798a8', fontSize: 10 }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#8798a8', fontSize: 10 }} tickFormatter={formatMoney} width={105} /><Tooltip formatter={(value, name) => [formatMoney(value), name]} contentStyle={{ border: '1px solid #e6edf4', borderRadius: 9, fontSize: 11 }} /><Bar dataKey="income" name="Income" fill="#55ae91" radius={[4, 4, 0, 0]} /><Bar dataKey="expenses" name="Expenses" fill="#438fc6" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div> : <div className="chart-empty">A date and amount column are needed for monthly trends.</div>}
      </article>
      <article className="dash-card chart-card"><div className="dash-card-heading"><div><h3>Income and expenses mix</h3><p>Based on the transaction direction and signs</p></div></div>
        {mix.length ? <div className="mix-chart-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={mix} dataKey="value" nameKey="name" innerRadius={59} outerRadius={82} paddingAngle={4} stroke="none">{mix.map((entry, index) => <Cell key={entry.name} fill={index === 0 ? '#55ae91' : '#438fc6'} />)}</Pie><Tooltip formatter={(value, name) => [formatMoney(value), name]} contentStyle={{ border: '1px solid #e6edf4', borderRadius: 9, fontSize: 11 }} /></PieChart></ResponsiveContainer><div className="mix-legend">{mix.map((item, index) => <span key={item.name}><i style={{ background: index === 0 ? '#55ae91' : '#438fc6' }} />{item.name}<b>{formatMoney(item.value)}</b></span>)}</div></div> : <div className="chart-empty">Upload rows with an amount column to see this summary.</div>}
      </article>
      <article className="dash-card chart-card category-chart-card"><div className="dash-card-heading"><div><h3>Category breakdown</h3><p>Top categories detected in the uploaded data</p></div></div>
        {categoryData.length ? <div className="analysis-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={categoryData} layout="vertical" margin={{ top: 3, right: 14, left: 8, bottom: 3 }}><CartesianGrid horizontal={false} stroke="#edf2f7" strokeDasharray="3 5" /><XAxis type="number" axisLine={false} tickLine={false} tick={{ fill: '#8798a8', fontSize: 10 }} tickFormatter={formatMoney} /><YAxis type="category" dataKey="category" width={92} axisLine={false} tickLine={false} tick={{ fill: '#647d91', fontSize: 10 }} /><Tooltip formatter={(value, name) => [formatMoney(value), name]} contentStyle={{ border: '1px solid #e6edf4', borderRadius: 9, fontSize: 11 }} /><Bar dataKey="income" name="Income" fill="#55ae91" radius={[0, 4, 4, 0]} /><Bar dataKey="expenses" name="Expenses" fill="#438fc6" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer></div> : <div className="chart-empty">A category and amount column are needed for category analysis.</div>}
      </article>
    </div>
  )
}

export default DashboardCharts
