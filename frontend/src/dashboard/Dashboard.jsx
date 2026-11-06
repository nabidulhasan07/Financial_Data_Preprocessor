import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  ArrowDownToLine,
  ArrowLeft,
  BarChart3,
  Check,
  ChevronDown,
  CircleDollarSign,
  ClipboardCheck,
  CloudUpload,
  Database,
  FileCheck2,
  FileSpreadsheet,
  FileWarning,
  LayoutDashboard,
  LoaderCircle,
  Menu,
  Rows3,
  ShieldCheck,
  Sparkles,
  WandSparkles,
  X,
} from 'lucide-react'
import {
  cleanDataset,
  downloadDataset,
  downloadQualityReportPdf,
  getHealth,
  getAnalysis,
  getApiError,
  getQualityReport,
  getValidation,
  uploadDataset,
} from '../services/api'
import DataTable from './DataTable'
import DashboardCharts from './DashboardCharts'
import { formatMoney } from '../utils/formatMoney'
import './Dashboard.css'

const navigation = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'upload', label: 'Upload Dataset', icon: CloudUpload },
  { id: 'cleaning', label: 'Data Cleaning', icon: WandSparkles },
  { id: 'validation', label: 'Data Validation', icon: ClipboardCheck },
  { id: 'analysis', label: 'Data Analysis', icon: BarChart3 },
  { id: 'reports', label: 'Reports', icon: FileCheck2 },
]

const statCards = [
  { key: 'total_transactions', label: 'Total Transactions', icon: Rows3, color: 'blue', format: (value) => Number(value).toLocaleString() },
  { key: 'total_income', label: 'Total Income', icon: CircleDollarSign, color: 'green', format: formatMoney },
  { key: 'total_expenses', label: 'Total Expenses', icon: ArrowDownToLine, color: 'purple', format: formatMoney },
  { key: 'missing_values', label: 'Missing Values', icon: AlertCircle, color: 'amber', format: (value) => Number(value).toLocaleString() },
  { key: 'duplicate_records', label: 'Duplicate Records', icon: Database, color: 'slate', format: (value) => Number(value).toLocaleString() },
]

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getDatasetStats(dataset) {
  if (!dataset) return {}
  return {
    ...dataset.analysis,
    missing_values: dataset.analysis.missing_values,
    duplicate_records: dataset.analysis.duplicate_records,
  }
}

function UploadBox({ onFile, busy, fileMeta, compact = false }) {
  const inputRef = useRef(null)
  const [dragActive, setDragActive] = useState(false)
  const [localError, setLocalError] = useState('')

  const selectFile = (file) => {
    setLocalError('')
    if (!file) return
    if (!/\.(csv|xlsx)$/i.test(file.name)) {
      setLocalError('Choose a CSV or Excel workbook (.csv or .xlsx).')
      return
    }
    if (file.size > 20 * 1024 * 1024) {
      setLocalError('This file is larger than the 20 MB upload limit.')
      return
    }
    onFile(file)
  }

  return (
    <div className={`upload-box${dragActive ? ' upload-box--active' : ''}${compact ? ' upload-box--compact' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragActive(true) }} onDragLeave={() => setDragActive(false)} onDrop={(event) => { event.preventDefault(); setDragActive(false); selectFile(event.dataTransfer.files?.[0]) }}>
      <input ref={inputRef} className="file-input" type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => { selectFile(event.target.files?.[0]); event.target.value = '' }} />
      <span className="upload-icon"><CloudUpload size={22} /></span>
      <div className="upload-copy"><h3>Drag and drop your dataset here</h3><p>or <button type="button" onClick={() => inputRef.current?.click()}>browse files</button></p><small>CSV or Excel (.xlsx) · up to 20 MB</small></div>
      <button className="button button--outline" type="button" onClick={() => inputRef.current?.click()} disabled={busy}>{busy ? <><LoaderCircle className="spin" size={16} /> Uploading</> : 'Choose file'}</button>
      {fileMeta && <div className="selected-file"><FileSpreadsheet size={16} /><span><b>{fileMeta.name}</b><small>{formatSize(fileMeta.size)}</small></span><Check size={16} /></div>}
      {localError && <p className="inline-error" role="alert">{localError}</p>}
    </div>
  )
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function formattedFinancialSummary(report) {
  const values = report.analysis
  return {
    total_income: formatMoney(values.total_income),
    total_expenses: formatMoney(values.total_expenses),
    net_cash_flow: formatMoney(values.total_income - values.total_expenses),
    average_transaction: formatMoney(values.average_transaction),
    category_summary: values.category_summary.map((item) => ({
      category: item.category,
      income: formatMoney(item.income),
      expenses: formatMoney(item.expenses),
    })),
    monthly_summary: values.monthly_summary.map((item) => ({
      month: item.month,
      income: formatMoney(item.income),
      expenses: formatMoney(item.expenses),
    })),
    missing_amount_fill_value: report.cleaning_summary?.missing_amount_fill_value === null
      ? null
      : formatMoney(report.cleaning_summary?.missing_amount_fill_value),
  }
}

function Dashboard({ onBack }) {
  const [active, setActive] = useState('overview')
  const [dataset, setDataset] = useState(null)
  const [fileMeta, setFileMeta] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [apiStatus, setApiStatus] = useState('checking')
  const [validationData, setValidationData] = useState(null)
  const [qualityData, setQualityData] = useState(null)
  const [cleaningOptions, setCleaningOptions] = useState({ missing_strategy: 'keep', remove_duplicates: true, standardize_dates: true, coerce_invalid_numbers: true })

  useEffect(() => {
    const controller = new AbortController()
    getHealth(controller.signal).then(() => setApiStatus('connected')).catch((requestError) => {
      if (requestError.name !== 'CanceledError') setApiStatus('disconnected')
    })
    return () => controller.abort()
  }, [])

  const loadFile = async (file) => {
    setBusy(true); setError(''); setNotice('')
    try {
      const result = await uploadDataset(file)
      setApiStatus('connected')
      setDataset(result); setFileMeta({ name: result.filename, size: file.size }); setValidationData(result.validation); setQualityData(null)
      setNotice(`Uploaded ${result.filename}. Review the preview, then choose a workflow section.`)
      setActive('overview')
    } catch (requestError) {
      setApiStatus('disconnected')
      setError(getApiError(requestError))
    } finally { setBusy(false) }
  }

  const navigate = async (id) => {
    setActive(id); setSidebarOpen(false); setError(''); setNotice('')
    if (!dataset) return
    try {
      if (id === 'validation') setValidationData(await getValidation(dataset.dataset_id))
      if (id === 'analysis') {
        const result = await getAnalysis(dataset.dataset_id)
        setDataset((current) => ({ ...current, analysis: result }))
      }
      if (id === 'reports') setQualityData(await getQualityReport(dataset.dataset_id))
      setApiStatus('connected')
    } catch (requestError) { setApiStatus('disconnected'); setError(getApiError(requestError)) }
  }

  const runCleaning = async () => {
    if (!dataset) return
    setBusy(true); setError(''); setNotice('')
    try {
      const result = await cleanDataset(dataset.dataset_id, cleaningOptions)
      setApiStatus('connected')
      setDataset(result); setValidationData(result.validation); setQualityData(null)
      const stats = result.cleaning_summary
      const amountSummary = stats.missing_amounts_filled > 0
        ? `Filled ${stats.missing_amounts_filled} missing amount${stats.missing_amounts_filled === 1 ? '' : 's'}${stats.missing_amount_fill_value !== null ? ` with ${formatMoney(stats.missing_amount_fill_value)}` : ''}.`
        : stats.missing_amounts_remaining > 0
          ? `Left ${stats.missing_amounts_remaining} unknown amount${stats.missing_amounts_remaining === 1 ? '' : 's'} unchanged; they are excluded from totals and averages.`
          : 'No unknown amounts remain.'
      setNotice(`Cleaning complete: handled ${stats.missing_values_handled} of ${stats.missing_values_detected} missing cells (${stats.missing_values_filled} filled, ${stats.missing_values_dropped} removed); ${stats.missing_values_remaining} remain. ${amountSummary} Removed ${stats.duplicates_removed} duplicates, standardized ${stats.dates_standardized} dates, and coerced ${stats.numbers_coerced} invalid amounts.`)
    } catch (requestError) { setApiStatus('disconnected'); setError(getApiError(requestError)) }
    finally { setBusy(false) }
  }

  const exportFile = async (format) => {
    if (!dataset) return
    setBusy(true); setError('')
    try {
      const blob = await downloadDataset(dataset.dataset_id, format)
      setApiStatus('connected')
      const stem = dataset.filename.replace(/\.[^.]+$/, '')
      downloadBlob(blob, `${stem}_cleaned.${format === 'csv' ? 'csv' : 'xlsx'}`)
      setNotice(`Your cleaned ${format.toUpperCase()} file has been downloaded.`)
    } catch (requestError) { setApiStatus('disconnected'); setError(getApiError(requestError)) }
    finally { setBusy(false) }
  }

  const exportQuality = async () => {
    if (!dataset) return
    setBusy(true); setError('')
    try {
      const report = qualityData ?? await getQualityReport(dataset.dataset_id)
      setApiStatus('connected')
      setQualityData(report)
      const displayReport = { ...report, formatted_financial_summary: formattedFinancialSummary(report) }
      downloadBlob(new Blob([JSON.stringify(displayReport, null, 2)], { type: 'application/json' }), `${dataset.filename.replace(/\.[^.]+$/, '')}_quality_report.json`)
      setNotice('Your data quality summary has been downloaded.')
    } catch (requestError) { setApiStatus('disconnected'); setError(getApiError(requestError)) }
    finally { setBusy(false) }
  }

  const exportQualityPdf = async () => {
    if (!dataset) return
    setBusy(true); setError('')
    try {
      const blob = await downloadQualityReportPdf(dataset.dataset_id)
      setApiStatus('connected')
      const stem = dataset.filename.replace(/\.[^.]+$/, '')
      downloadBlob(blob, `${stem}_visual_quality_report.pdf`)
      setNotice('Your visual financial quality report has been downloaded.')
    } catch (requestError) { setApiStatus('disconnected'); setError(getApiError(requestError)) }
    finally { setBusy(false) }
  }

  const activeItem = navigation.find((item) => item.id === active) ?? navigation[0]
  const stats = getDatasetStats(dataset)
  const showUpload = active === 'upload' || (!dataset && active === 'overview')

  return (
    <div className="dashboard-app">
      {sidebarOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <aside className={`dashboard-sidebar${sidebarOpen ? ' dashboard-sidebar--open' : ''}`}>
        <div className="sidebar-brand-row"><a className="dash-brand" href="#dashboard" onClick={(event) => { event.preventDefault(); navigate('overview') }}><span className="dash-brand-mark"><BarChart3 size={18} /></span><span>fin<span>prep</span></span></a><button className="sidebar-close" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}><X size={19} /></button></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="sidebar-nav" aria-label="Dashboard sections">{navigation.map(({ id, label, icon: Icon }) => <button key={id} className={`sidebar-link${active === id ? ' sidebar-link--active' : ''}`} onClick={() => navigate(id)}><Icon size={17} strokeWidth={1.8} /><span>{label}</span>{id === 'validation' && dataset && dataset.validation.count > 0 && <span className="nav-count">{dataset.validation.count}</span>}</button>)}</nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-storage"><div className="storage-title"><ShieldCheck size={16} /><b>Private workspace</b></div><p>Uploads are processed temporarily in memory and are cleared on server restart.</p></div>
        <button className="back-home" onClick={onBack}><ArrowLeft size={16} /> Back to home</button>
      </aside>

      <div className="dashboard-main">
        <header className="dashboard-topbar"><button className="dashboard-menu" aria-label="Open navigation" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button><div className="breadcrumbs"><span>Workspace</span><i>/</i><b>{activeItem.label}</b></div><div className="topbar-right"><span className={`connection-pill connection-pill--${apiStatus}`}><span />{apiStatus === 'connected' ? 'API connected' : apiStatus === 'checking' ? 'Checking API' : 'API unavailable'}</span><span className="user-avatar">FP</span></div></header>
        <main className="dashboard-content">
          <div className="page-heading"><div><div className="dashboard-eyebrow"><Sparkles size={13} /> FINANCIAL DATA WORKSPACE</div><h1>{active === 'overview' ? 'Overview' : activeItem.label}</h1><p>{active === 'overview' ? 'Your dataset, quality checks, and financial picture in one place.' : pageDescription(active)}</p></div>{dataset && <div className="dataset-chip"><FileSpreadsheet size={16} /><span>{dataset.filename}</span><ChevronDown size={14} /></div>}</div>

          {error && <div className="feedback feedback--error" role="alert"><AlertCircle size={17} />{error}<button onClick={() => setError('')} aria-label="Dismiss error"><X size={16} /></button></div>}
          {notice && <div className="feedback feedback--success" role="status"><Check size={17} />{notice}<button onClick={() => setNotice('')} aria-label="Dismiss notice"><X size={16} /></button></div>}

          {active === 'overview' && <>
            <section className="stats-grid" aria-label="Financial dataset summary">{statCards.map(({ key, label, icon: Icon, color, format }) => <article className="stat-card" key={key}><div className={`stat-icon stat-icon--${color}`}><Icon size={18} /></div><span>{label}</span><strong>{dataset ? format(stats[key] ?? 0) : '—'}</strong><small>{dataset ? 'From current dataset' : 'Upload a dataset to calculate'}</small></article>)}</section>
            {showUpload && <section className="dash-card upload-section"><div className="dash-card-heading"><div><h2>Upload your financial data</h2><p>Start with a transaction export or spreadsheet.</p></div></div><UploadBox onFile={loadFile} busy={busy} fileMeta={fileMeta} /></section>}
            {dataset && <><DataTable dataset={dataset} /><div className="overview-lower"><article className="dash-card quick-actions"><div className="dash-card-heading"><div><h3>Continue your workflow</h3><p>Review the data, resolve issues, and explore the results.</p></div></div><div className="quick-action-grid"><button onClick={() => navigate('cleaning')}><span className="quick-icon quick-icon--blue"><WandSparkles size={17} /></span><span><b>Clean data</b><small>Handle gaps and duplicates</small></span><ArrowDownToLine size={16} /></button><button onClick={() => navigate('validation')}><span className="quick-icon quick-icon--amber"><FileWarning size={17} /></span><span><b>Review validation</b><small>{dataset.validation.count} issue{dataset.validation.count === 1 ? '' : 's'} detected</small></span><ArrowDownToLine size={16} /></button><button onClick={() => navigate('analysis')}><span className="quick-icon quick-icon--green"><BarChart3 size={17} /></span><span><b>View analysis</b><small>Summaries and charts</small></span><ArrowDownToLine size={16} /></button></div></article></div></>}
          </>}

          {active === 'upload' && <section className="dash-card upload-section"><div className="dash-card-heading"><div><h2>Upload a dataset</h2><p>Import a CSV or Excel workbook to preview and process financial records.</p></div></div><UploadBox onFile={loadFile} busy={busy} fileMeta={fileMeta} />{dataset && <div className="upload-details"><span><FileSpreadsheet size={16} /> Current file <b>{dataset.filename}</b></span><span><Rows3 size={16} /> {dataset.row_count.toLocaleString()} rows</span><button className="text-action" onClick={() => navigate('overview')}>View preview <ArrowLeft size={14} /></button></div>}</section>}

          {active === 'cleaning' && <>
            {!dataset ? <NoDataset onUpload={() => navigate('upload')} /> : <><section className="dash-card cleaning-options"><div className="dash-card-heading"><div><h2>Cleaning options</h2><p>Choose how Pandas should handle the current dataset.</p></div><span className={`state-badge${dataset.cleaned ? ' state-badge--done' : ''}`}>{dataset.cleaned ? <><Check size={13} /> Cleaned</> : 'Not cleaned yet'}</span></div>
              <div className="cleaning-option-grid"><label className="cleaning-select"><span>Missing values and amounts</span><select value={cleaningOptions.missing_strategy} onChange={(event) => setCleaningOptions({ ...cleaningOptions, missing_strategy: event.target.value })}><option value="keep">Leave missing amounts unchanged</option><option value="fill_zero">Fill missing amounts with 0</option><option value="fill_mean">Fill missing amounts with the mean</option><option value="fill_median">Fill missing amounts with the median</option><option value="drop_rows">Remove rows with missing values</option></select><small>{dataset.analysis.missing_values.toLocaleString()} missing cell{dataset.analysis.missing_values === 1 ? '' : 's'}, including {dataset.analysis.missing_amounts.toLocaleString()} missing amount{dataset.analysis.missing_amounts === 1 ? '' : 's'}. Unchanged amounts stay unknown, not zero.</small></label>
                <ToggleOption title="Remove duplicate records" detail={`${dataset.analysis.duplicate_records} exact duplicate row${dataset.analysis.duplicate_records === 1 ? '' : 's'} detected.`} checked={cleaningOptions.remove_duplicates} onChange={(checked) => setCleaningOptions({ ...cleaningOptions, remove_duplicates: checked })} />
                <ToggleOption title="Standardize date formats" detail={dataset.analysis.detected_columns.date ? `Detected date column: ${dataset.analysis.detected_columns.date}` : 'No date-like column was recognized.'} checked={cleaningOptions.standardize_dates} onChange={(checked) => setCleaningOptions({ ...cleaningOptions, standardize_dates: checked })} disabled={!dataset.analysis.detected_columns.date} />
                <ToggleOption title="Coerce invalid amounts" detail={dataset.analysis.detected_columns.amount ? `Invalid numbers in ${dataset.analysis.detected_columns.amount} become blank values.` : 'No amount-like column was recognized.'} checked={cleaningOptions.coerce_invalid_numbers} onChange={(checked) => setCleaningOptions({ ...cleaningOptions, coerce_invalid_numbers: checked })} disabled={!dataset.analysis.detected_columns.amount} />
              </div><button className="button button--dashboard" onClick={runCleaning} disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <WandSparkles size={16} />}{busy ? 'Cleaning dataset' : 'Clean dataset'}</button>
            </section><DataTable dataset={dataset} /></>}
          </>}

          {active === 'validation' && (!dataset ? <NoDataset onUpload={() => navigate('upload')} /> : <section className="dash-card validation-card"><div className="dash-card-heading"><div><h2>Validation results</h2><p>Checks for unparseable dates, invalid amounts, and negative income values.</p></div><span className={`validation-count${(validationData?.count ?? 0) ? ' validation-count--issues' : ''}`}>{validationData?.count ?? 0} issues</span></div>{validationData?.issues?.length ? <div className="issue-list">{validationData.issues.map((issue, index) => <article className="issue-row" key={`${issue.row}-${issue.column}-${index}`}><span className="issue-icon"><AlertCircle size={16} /></span><div><b>Row {issue.row} · {issue.column}</b><p>{issue.message}</p></div><code>{issue.column === dataset.analysis.detected_columns.amount ? formatMoney(issue.value) : issue.value ?? '—'}</code></article>)}</div> : <div className="validation-empty"><span><ShieldCheck size={23} /></span><h3>No validation issues found</h3><p>The current data passed the available date and amount checks.</p></div>}{validationData?.truncated && <div className="table-card-footer">Showing the first 500 issues. The API found additional records.</div>}</section>)}

          {active === 'analysis' && (!dataset ? <NoDataset onUpload={() => navigate('upload')} /> : <><div className="calculation-note"><AlertCircle size={16} />{dataset.analysis.unknown_amounts.toLocaleString()} missing or invalid amount{dataset.analysis.unknown_amounts === 1 ? '' : 's'} excluded from financial calculations. Unknown amounts are not treated as zero.</div><section className="analysis-summary"><article><span>Average transaction</span><strong>{formatMoney(dataset.analysis.average_transaction)}</strong><small>Valid amounts only</small></article><article><span>Net cash flow</span><strong>{formatMoney(dataset.analysis.total_income - dataset.analysis.total_expenses)}</strong><small>Income less expenses</small></article><article><span>Records analyzed</span><strong>{dataset.row_count.toLocaleString()}</strong><small>Current processed rows</small></article></section><DashboardCharts analysis={dataset.analysis} /><DataTable dataset={dataset} /></>)}

          {active === 'reports' && (!dataset ? <NoDataset onUpload={() => navigate('upload')} /> : <><section className="dash-card report-card"><div className="report-icon"><FileCheck2 size={21} /></div><div className="report-copy"><h2>Data quality summary</h2><p>Download a visual PDF with charts and recommendations, or keep the detailed JSON report.</p></div><div className="report-download-actions"><button className="button button--dashboard" onClick={exportQualityPdf} disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <FileCheck2 size={16} />} Download PDF</button><button className="button button--outline" onClick={exportQuality} disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <ArrowDownToLine size={16} />} Download JSON</button></div></section>
            <section className="dash-card export-card"><div className="dash-card-heading"><div><h2>Export cleaned data</h2><p>Download the current dataset processed by the backend.</p></div></div><div className="export-actions"><button onClick={() => exportFile('csv')} disabled={busy}><FileSpreadsheet size={18} /><span><b>Export CSV</b><small>Comma-separated values</small></span><ArrowDownToLine size={17} /></button><button onClick={() => exportFile('xlsx')} disabled={busy}><FileSpreadsheet size={18} /><span><b>Export Excel</b><small>Microsoft Excel workbook</small></span><ArrowDownToLine size={17} /></button></div></section>
            {qualityData && <section className="dash-card quality-preview"><div className="dash-card-heading"><div><h3>Report preview</h3><p>Latest quality metrics from the API</p></div></div><div className="quality-metrics"><span><b>{qualityData.row_count.toLocaleString()}</b> rows</span><span><b>{qualityData.column_count}</b> columns</span><span><b>{qualityData.missing_values.toLocaleString()}</b> missing values</span><span><b>{qualityData.duplicate_records.toLocaleString()}</b> duplicates</span><span><b>{qualityData.validation.count.toLocaleString()}</b> validation issues</span></div><div className="report-money-preview"><span>Income <b>{formatMoney(qualityData.analysis.total_income)}</b></span><span>Expenses <b>{formatMoney(qualityData.analysis.total_expenses)}</b></span><span>Average <b>{formatMoney(qualityData.analysis.average_transaction)}</b></span><span>Net cash flow <b>{formatMoney(qualityData.analysis.total_income - qualityData.analysis.total_expenses)}</b></span></div></section>}</>)}
        </main>
      </div>
    </div>
  )
}

function pageDescription(id) {
  const descriptions = { upload: 'Bring in the CSV or Excel file you want to prepare.', cleaning: 'Choose transparent steps to prepare records for analysis.', validation: 'Review detected financial data issues before using the results.', analysis: 'Explore the summaries and trends found in your dataset.', reports: 'Export processed datasets and data quality findings.' }
  return descriptions[id] ?? ''
}

function ToggleOption({ title, detail, checked, onChange, disabled = false }) {
  return <label className={`toggle-option${disabled ? ' toggle-option--disabled' : ''}`}><span className="toggle-copy"><b>{title}</b><small>{detail}</small></span><input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} /><span className="toggle-control" /></label>
}

function NoDataset({ onUpload }) {
  return <div className="empty-state empty-state--large"><span><CloudUpload size={24} /></span><h3>Upload a dataset to continue</h3><p>This section uses real records processed by the FastAPI backend.</p><button className="button button--dashboard" onClick={onUpload}>Upload dataset <CloudUpload size={15} /></button></div>
}

export default Dashboard
