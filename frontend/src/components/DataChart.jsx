import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from 'recharts'
import { formatMoney } from '../utils/formatMoney'

function DataChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="cashFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#48a8e2" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#48a8e2" stopOpacity={0.01} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="#edf2f7" strokeDasharray="3 5" />
        <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#9aabba', fontSize: 10 }} tickMargin={10} />
        <Tooltip contentStyle={{ border: '1px solid #e6edf4', borderRadius: 10, boxShadow: '0 6px 20px #17344d14', fontSize: 12 }} formatter={formatMoney} />
        <Area type="monotone" dataKey="value" stroke="#398fcc" strokeWidth={2.6} fill="url(#cashFill)" activeDot={{ r: 4, fill: '#398fcc', stroke: '#fff', strokeWidth: 2 }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export default DataChart
