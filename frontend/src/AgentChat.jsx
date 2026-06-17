// AgentChat.jsx
// Drop alongside App.jsx, IntegrationTool.jsx, ReleasechangeTools.jsx

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box, Typography, TextField, Button, Card, CardContent,
  Chip, Paper, CircularProgress, LinearProgress, Alert,
  Avatar, Divider, Tooltip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions,
  Grid
} from '@mui/material';

import SmartToyIcon       from '@mui/icons-material/SmartToy';
import SendIcon           from '@mui/icons-material/Send';
import RouteIcon          from '@mui/icons-material/AltRoute';
import SearchIcon         from '@mui/icons-material/Search';
import CheckCircleIcon    from '@mui/icons-material/CheckCircle';
import ErrorOutlineIcon   from '@mui/icons-material/ErrorOutlined';
import HelpOutlineIcon from "@mui/icons-material/HelpOutlineOutlined";
import StorageIcon        from '@mui/icons-material/Storage';
import CleaningServicesIcon from '@mui/icons-material/CleaningServices';
import SyncAltIcon        from '@mui/icons-material/SyncAlt';
import RocketLaunchIcon   from '@mui/icons-material/RocketLaunch';
import AddBoxIcon         from '@mui/icons-material/AddBox';
import VpnKeyIcon         from '@mui/icons-material/VpnKey';


import FilterListIcon        from '@mui/icons-material/FilterList';
import OpenInNewIcon         from '@mui/icons-material/OpenInNew';
import WarningAmberIcon      from '@mui/icons-material/WarningAmber';
import HighlightOffIcon      from '@mui/icons-material/HighlightOff';
import RecommendIcon         from '@mui/icons-material/Recommend';
import FlagIcon              from '@mui/icons-material/Flag';
import BugReportIcon         from '@mui/icons-material/BugReport';
import CodeIcon              from '@mui/icons-material/Code';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

// import BlueprintValidator from './BlueprintValidator';
import ATFResults from './ATFResults';
// ADD to AgentChat.jsx imports at top
import { ModernizeDialog } from './IntegrationTool';
import DiscoveryPanel from './DiscoveryPanel';
import BlueprintPreview from './BlueprintPreview';

import ScienceIcon from '@mui/icons-material/Science';

const API_BASE  = 'http://127.0.0.1:8000';
const SESSION_ID = crypto.randomUUID();  // one session per browser tab

// ── Intent → MUI colour + icon ──────────────────────────────────────────────
const INTENT_CFG = {
  new_module:  { color: '#6366f1', bg: '#eef2ff', label: 'New Module Development',             icon: <AddBoxIcon /> },
  scoped_app:  { color: '#22c55e', bg: '#f0fdf4', label: 'Scoped App Development',             icon: <VpnKeyIcon /> },
  integration: { color: '#f97316', bg: '#fff7ed', label: 'Integration & Modernization',        icon: <SyncAltIcon /> },
  tech_debt:   { color: '#ef4444', bg: '#fef2f2', label: 'Technical Debt Clearance',           icon: <CleaningServicesIcon /> },
  release:     { color: '#0ea5e9', bg: '#f0f9ff', label: 'Release & Change Management',        icon: <RocketLaunchIcon /> },
};

const EXAMPLES = [
  'Scan for unused business rules and stale script includes',
  'Modernise the legacy SOAP integrations in my instance',
  'Check release readiness for CHG0040007',
  'Scaffold a scoped app called IT Asset Management',
  'Create a new Vendor Management module with approval workflow',
];

// ── Typing dots (pure CSS animation via sx keyframes) ────────────────────────
function TypingDots() {
  return (
    <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', py: 1 }}>
      {[0, 1, 2].map(i => (
        <Box key={i} sx={{
          width: 7, height: 7, borderRadius: '50%', bgcolor: '#94a3b8',
          animation: 'bounce 1.2s infinite',
          animationDelay: `${i * 0.2}s`,
          '@keyframes bounce': {
            '0%, 80%, 100%': { transform: 'scale(0.8)', opacity: 0.5 },
            '40%':            { transform: 'scale(1.2)', opacity: 1   },
          }
        }} />
      ))}
    </Box>
  );
}

// ── Pre-scan count chips ──────────────────────────────────────────────────────
function PreScanCounts({ prescan }) {
  const skip    = new Set(['hint']);
  const entries = Object.entries(prescan).filter(([k]) => !skip.has(k));
  if (!entries.length) return null;
  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
      {entries.map(([k, v]) => (
        <Paper key={k} elevation={0} sx={{
          px: 1.5, py: 0.5, border: '1px solid #e2e8f0',
          borderRadius: 2, textAlign: 'center', minWidth: 64,
        }}>
          <Typography variant="h6" fontWeight="bold" sx={{ lineHeight: 1.2, color: '#1e293b' }}>
            {v}
          </Typography>
          <Typography variant="caption" sx={{ color: '#94a3b8', textTransform: 'capitalize', fontSize: '0.68rem' }}>
            {k.replace(/_/g, ' ')}
          </Typography>
        </Paper>
      ))}
    </Box>
  );
}

// ── Risk colour map (mirrors App.jsx) ────────────────────────────────────────
const RISK_COLOR = {
  High:   { bg: '#fef2f2', border: '#fca5a5', text: '#dc2626', chip: 'error'   },
  Medium: { bg: '#fffbeb', border: '#fcd34d', text: '#d97706', chip: 'warning' },
  Low:    { bg: '#f0fdf4', border: '#86efac', text: '#16a34a', chip: 'success' },
  None:   { bg: '#f8fafc', border: '#cbd5e1', text: '#64748b', chip: 'default' },
};

const URGENCY_CFG = {
  Critical: { bg: '#fef2f2', border: '#fca5a5', text: '#dc2626', bar: '#dc2626' },
  High:     { bg: '#fff7ed', border: '#fed7aa', text: '#ea580c', bar: '#ea580c' },
  Medium:   { bg: '#fffbeb', border: '#fcd34d', text: '#d97706', bar: '#d97706' },
  Low:      { bg: '#f0fdf4', border: '#86efac', text: '#16a34a', bar: '#16a34a' },
  None:     { bg: '#f0f9ff', border: '#7dd3fc', text: '#0284c7', bar: '#0284c7' },
};

const scoreColor = (s) =>
  s <= 30 ? '#dc2626' : s <= 50 ? '#ea580c' : s <= 70 ? '#d97706' : s <= 85 ? '#16a34a' : '#0284c7';

const DEACTIVATE_BLOCKED_TABLES = new Set([
  'sys_security_acl', 'sys_dictionary', 'sys_db_object', 'sys_properties',
]);

const RiskChip = ({ level }) => {
  const cfg   = RISK_COLOR[level] || RISK_COLOR.None;
  const icons = {
    High:   <ErrorOutlineIcon />,
    Medium: <WarningAmberIcon />,
    Low:    <InfoOutlinedIcon />,
    None:   <CheckCircleIcon />,
  };
  return (
    <Chip icon={icons[level] || icons.None} label={level || 'None'}
      size="small" color={cfg.chip} variant="filled"
      sx={{ fontWeight: 'bold', fontSize: '0.75rem' }} />
  );
};

const FlagBadgeDebt = ({ flag }) => {
  const color =
    flag.includes('eval') || flag.includes('sleep') || flag.includes('hardcoded') ? '#dc2626'
    : flag.includes('inactive') || flag.includes('stale') ? '#d97706'
    : '#64748b';
  return (
    <Chip label={flag} size="small" sx={{
      fontFamily: 'monospace', fontSize: '0.7rem',
      bgcolor: `${color}15`, color,
      border: `1px solid ${color}40`, height: 22,
    }} />
  );
};

function AgentFindingDetailDialog({ finding, open, onClose, onDeactivated, onModernizeClick  }) {
  const [confirmOpen,      setConfirmOpen]      = useState(false);
  const [deactivating,     setDeactivating]     = useState(false);
  const [deactivateResult, setDeactivateResult] = useState(null);
  const [isActive,         setIsActive]         = useState(null);

  useEffect(() => {
    if (finding) {
      setIsActive(finding.active === 'true' || finding.active === true);
      setDeactivateResult(null);
    }
  }, [finding]);

  if (!finding) return null;
  const riskCfg = RISK_COLOR[finding.risk_level] || RISK_COLOR.None;

  const canDeactivate =
    isActive &&
    !DEACTIVATE_BLOCKED_TABLES.has(finding.table_source) &&
    ['High', 'Medium', 'Low'].includes(finding.risk_level);

  const handleDeactivate = async () => {
    setConfirmOpen(false);
    setDeactivating(true);
    setDeactivateResult(null);
    try {
      const res  = await fetch(`${API_BASE}/api/deactivate-record`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          table:  finding.table_source,
          sys_id: finding.sys_id,
          name:   finding.name,
        }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setIsActive(false);
        setDeactivateResult({ success: true, message: data.message });
        if (onDeactivated) onDeactivated(finding.sys_id);
      } else {
        setDeactivateResult({ success: false, message: data.message });
      }
    } catch (err) {
      setDeactivateResult({ success: false, message: `Request failed: ${err.message}` });
    } finally {
      setDeactivating(false);
    }
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth
        PaperProps={{ sx: { borderRadius: 3, border: `2px solid ${riskCfg.border}` } }}>

        <DialogTitle sx={{ bgcolor: riskCfg.bg, borderBottom: `1px solid ${riskCfg.border}`, pb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <CodeIcon sx={{ color: riskCfg.text }} />
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6" fontWeight="bold">{finding.name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {finding.label} · {finding.table_source}
              </Typography>
            </Box>
            <RiskChip level={finding.risk_level} />
            <Chip size="small"
              label={isActive ? 'Active' : 'Inactive'}
              icon={isActive ? <CheckCircleIcon /> : <HighlightOffIcon />}
              color={isActive ? 'success' : 'default'}
              variant="outlined" />
          </Box>
        </DialogTitle>

        <DialogContent sx={{ pt: 3 }}>
          {deactivateResult && (
            <Alert severity={deactivateResult.success ? 'success' : 'error'}
              sx={{ mb: 2 }} onClose={() => setDeactivateResult(null)}>
              {deactivateResult.success
                ? `✅ ${deactivateResult.message} — Record is now inactive in ServiceNow.`
                : `❌ ${deactivateResult.message}`}
            </Alert>
          )}

          <Grid container spacing={3}>
            {/* Metadata */}
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>
                METADATA
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8 }}>
                {[
                  ['Active',       isActive ? '✅ Yes' : '❌ No'],
                  ['Last Updated', finding.last_updated || '—'],
                  ['Updated By',   finding.updated_by   || '—'],
                  ['Table',        finding.table_source],
                ].map(([k, v]) => (
                  <Box key={k} sx={{ display: 'flex', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 110 }}>{k}:</Typography>
                    <Typography variant="body2" fontWeight="medium">{v}</Typography>
                  </Box>
                ))}
                {finding.extra && Object.entries(finding.extra).filter(([, v]) => v).map(([k, v]) => (
                  <Box key={k} sx={{ display: 'flex', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary"
                      sx={{ minWidth: 110, textTransform: 'capitalize' }}>
                      {k.replace(/_/g, ' ')}:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">{String(v)}</Typography>
                  </Box>
                ))}
              </Box>
            </Grid>

            {/* Flags */}
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>
                DETECTED FLAGS
              </Typography>
              {finding.basic_flags?.length > 0
                ? <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.8 }}>
                    {finding.basic_flags.map((f, i) => <FlagBadgeDebt key={i} flag={f} />)}
                  </Box>
                : <Typography variant="body2" color="text.secondary">No flags detected</Typography>
              }
            </Grid>

            {/* AI Summary */}
            {finding.ai_summary && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>
                  AI SUMMARY
                </Typography>
                <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8fafc', borderRadius: 2, border: '1px solid #e2e8f0' }}>
                  <Typography variant="body2">{finding.ai_summary}</Typography>
                </Paper>
              </Grid>
            )}

            {/* AI Issues */}
            {finding.ai_issues?.length > 0 && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1.5 }}>
                  ISSUES FOUND
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {finding.ai_issues.map((issue, i) => (
                    <Paper key={i} elevation={0} sx={{
                      p: 2, borderRadius: 2,
                      border: `1px solid ${riskCfg.border}`,
                      bgcolor: riskCfg.bg,
                    }}>
                      <Typography variant="body2" fontWeight="bold" color={riskCfg.text} sx={{ mb: 0.5 }}>
                        {issue.type}
                      </Typography>
                      <Typography variant="body2">{issue.detail}</Typography>
                      {issue.line_hint && issue.line_hint !== 'N/A' && (
                        <Typography variant="caption" sx={{
                          fontFamily: 'monospace', bgcolor: '#1e293b',
                          color: '#a6e22e', px: 1, py: 0.3,
                          borderRadius: 1, display: 'inline-block', mt: 0.5,
                        }}>
                          {issue.line_hint}
                        </Typography>
                      )}
                    </Paper>
                  ))}
                </Box>
              </Grid>
            )}

            {/* Recommendation */}
            {finding.recommendation && finding.recommendation !== 'No action required.' && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>
                  RECOMMENDATION
                </Typography>
                <Paper elevation={0} sx={{ p: 2, bgcolor: '#f0fdf4', border: '1px solid #86efac', borderRadius: 2 }}>
                  <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                    <RecommendIcon sx={{ color: '#16a34a', mt: 0.2, flexShrink: 0 }} />
                    <Typography variant="body2">{finding.recommendation}</Typography>
                  </Box>
                </Paper>
              </Grid>
            )}

            {DEACTIVATE_BLOCKED_TABLES.has(finding.table_source) && (
              <Grid item xs={12}>
                <Alert severity="info">
                  Deactivation disabled for <strong>{finding.table_source}</strong> — protected system table.
                </Alert>
              </Grid>
            )}
          </Grid>
        </DialogContent>

        <DialogActions sx={{ p: 2.5, borderTop: '1px solid #e2e8f0', gap: 1 }}>
          <Button onClick={onClose} variant="outlined" sx={{ mr: 'auto' }}>Close</Button>
          <Button variant="outlined" startIcon={<OpenInNewIcon />}
            onClick={() => window.open(
              `https://abhrademo5.service-now.com/nav_to.do?uri=${finding.table_source}.do?sys_id=${finding.sys_id}`,
              '_blank'
            )}>
            Open in ServiceNow
          </Button>
          {canDeactivate && (
            <Button variant="contained" color="warning"
              startIcon={deactivating
                ? <CircularProgress size={16} color="inherit" />
                : <HighlightOffIcon />}
              onClick={() => setConfirmOpen(true)}
              disabled={deactivating}
              sx={{ bgcolor: '#d97706', '&:hover': { bgcolor: '#b45309' } }}>
              {deactivating ? 'Deactivating...' : 'Deactivate Record'}
            </Button>
          )}
          {!isActive && !DEACTIVATE_BLOCKED_TABLES.has(finding.table_source) && (
            <Chip icon={<CheckCircleIcon />} label="Already Inactive"
              color="default" variant="outlined" size="small" />
          )}

          {/* Modernize button — only for integration findings with urgency */}
          {finding.urgency && finding.urgency !== 'None' && onModernizeClick && (
            <Button
              variant="contained"
              onClick={() => { onClose(); onModernizeClick(); }}
              sx={{ bgcolor: '#7c3aed', '&:hover': { bgcolor: '#6d28d9' } }}
            >
              Preview Modernization
            </Button>
          )}

        </DialogActions>
      </Dialog>

      {/* Confirm dialog */}
      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} maxWidth="xs" fullWidth
        PaperProps={{ sx: { borderRadius: 3, border: '2px solid #fcd34d' } }}>
        <DialogTitle sx={{ bgcolor: '#fffbeb', borderBottom: '1px solid #fcd34d' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <WarningAmberIcon sx={{ color: '#d97706' }} />
            <Typography fontWeight="bold">Confirm Deactivation</Typography>
          </Box>
        </DialogTitle>
        <DialogContent sx={{ pt: 3 }}>
          <Typography variant="body2" sx={{ mb: 2 }}>You are about to deactivate:</Typography>
          <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8fafc', borderRadius: 2, border: '1px solid #e2e8f0', mb: 2 }}>
            <Typography variant="body2" fontWeight="bold">{finding.name}</Typography>
            <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#64748b' }}>
              {finding.table_source}
            </Typography>
          </Paper>
          <Alert severity="warning" sx={{ mb: 1 }}>
            This sets <strong>active = false</strong>. The script stops executing immediately.
          </Alert>
          <Alert severity="info">Fully reversible from ServiceNow.</Alert>
        </DialogContent>
        <DialogActions sx={{ p: 2, gap: 1 }}>
          <Button onClick={() => setConfirmOpen(false)} variant="outlined" fullWidth>Cancel</Button>
          <Button onClick={handleDeactivate} variant="contained" color="warning" fullWidth
            sx={{ bgcolor: '#d97706', '&:hover': { bgcolor: '#b45309' } }}>
            Yes, Deactivate
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

// ── Result renderer — pretty-prints the final data object ─────────────────────
// In AgentChat.jsx, REPLACE the ResultBlock function

// REPLACE the entire ResultBlock function

function ResultBlock({ result, intent }) {
  const [riskFilter,     setRiskFilter]     = useState('All');
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [dialogOpen,     setDialogOpen]     = useState(false);
  const [deactivatedIds, setDeactivatedIds] = useState(new Set());
  const [modernizeOpen,   setModernizeOpen]   = useState(false);
  const [modernizedIds,   setModernizedIds]   = useState(new Set());

  const isBuild   = ['new_module', 'scoped_app'].includes(intent);
  const isScan    = ['tech_debt', 'integration'].includes(intent);
  const isRelease = intent === 'release';
  const summary   = result?.summary;

  // const releaseData = isRelease ? (
  //   result?.production_readiness ? result
  //   : result?.readiness ? { ...result.readiness, change_number: result.change_number, table: result.table }
  //   : null
  // ) : null;

  const releaseData = isRelease
  ? result?.production_readiness
    ? result                                                      // flat shape (your actual API)
    : result?.readiness
      ? { ...result.readiness,
          change_number: result.change_number,
          table: result.table }                                   // nested shape (legacy)
      : null
  : null;

  const handleDeactivated = (sys_id) => {
    setDeactivatedIds(prev => new Set([...prev, sys_id]));
  };

  const handleApplied = (sys_id, applyResult) => {
    if (applyResult.status === 'completed') {
      setModernizedIds(prev => new Set([...prev, sys_id]));
    }
  };

  const filteredFindings = (result?.findings || []).filter(f =>
    riskFilter === 'All' ? true : f.risk_level === riskFilter
  );

  return (
    <Box>
      {/* ── Completion banner ── */}
      <Alert severity="success" icon={<CheckCircleIcon />} sx={{ mb: 2, borderRadius: 2 }}>
        {result?.message || 'Task completed successfully.'}
      </Alert>

      {/* ── BUILD results ── */}
      {/* {isBuild && (
        <Box>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, mb: 2 }}>
            {[
              { label: 'Tables',        value: result.tables_created?.length,        color: '#3b82f6' },
              { label: 'Fields',        value: result.fields_created?.length,        color: '#6366f1' },
              { label: 'Roles',         value: result.roles_created?.length,         color: '#f59e0b' },
              { label: 'Workflows',     value: result.workflows_created?.length,     color: '#10b981' },
              { label: 'Forms',         value: result.forms_created?.length,         color: '#8b5cf6' },
              { label: 'ACLs',          value: result.acls_created?.length,          color: '#ef4444' },
              { label: 'Notifications', value: result.notifications_created?.length, color: '#0ea5e9' },
              { label: 'Navigation',    value: result.navigation_created?.length,    color: '#64748b' },
            ].filter(s => s.value > 0).map(s => (
              <Paper key={s.label} elevation={0} sx={{
                border: `1px solid ${s.color}30`, borderTop: `3px solid ${s.color}`,
                borderRadius: 2, px: 2, py: 1, textAlign: 'center', minWidth: 72,
              }}>
                <Typography variant="h5" fontWeight="bold" sx={{ color: s.color, lineHeight: 1 }}>
                  {s.value}
                </Typography>
                <Typography variant="caption" color="text.secondary">{s.label}</Typography>
              </Paper>
            ))}
          </Box>
          {result?.app_scope && (
            <Paper elevation={0} sx={{
              px: 2, py: 1, mb: 2, border: '1px solid #e2e8f0',
              borderRadius: 2, display: 'inline-flex', gap: 1, alignItems: 'center',
            }}>
              <Typography variant="caption" color="text.secondary">Scope:</Typography>
              <Typography variant="body2" fontWeight="bold" sx={{ fontFamily: 'monospace' }}>
                {result.app_scope}
              </Typography>
              {result.app_sys_id && (
                <>
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>sys_id:</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: 11, color: '#64748b' }}>
                    {result.app_sys_id}
                  </Typography>
                </>
              )}
            </Paper>
          )}
        </Box>
      )} */}

      {/* ── SCAN summary stat cards ── */}
      {isScan && summary && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, mb: 2 }}>
          {[
            { label: 'Total',   value: summary.total_scanned,              color: '#3b82f6' },
            { label: 'High',    value: summary.high_risk ?? summary.critical, color: '#dc2626' },
            { label: 'Medium',  value: summary.medium_risk ?? summary.high,   color: '#d97706' },
            { label: 'Low',     value: summary.low_risk ?? summary.medium,    color: '#16a34a' },
            { label: 'Inactive', value: summary.inactive,                  color: '#7c3aed' },
            { label: 'Stale',   value: summary.stale,                      color: '#0891b2' },
          ].filter(s => s.value !== undefined && s.value !== null).map(s => (
            <Paper key={s.label} elevation={0} sx={{
              border: `1px solid ${s.color}30`, borderTop: `3px solid ${s.color}`,
              borderRadius: 2, px: 2, py: 1, minWidth: 68, textAlign: 'center',
            }}>
              <Typography variant="h5" fontWeight="bold" sx={{ color: s.color, lineHeight: 1 }}>
                {s.value ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">{s.label}</Typography>
            </Paper>
          ))}
        </Box>
      )}

      {/* ── SCAN findings table (tech_debt) ── */}
      {intent === 'tech_debt' && result?.findings?.length > 0 && (
        <Box>
          {/* Risk filter buttons */}
          <Box sx={{ display: 'flex', gap: 1, mb: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
            <FilterListIcon sx={{ color: '#94a3b8', fontSize: 18 }} />
            {['All', 'High', 'Medium', 'Low', 'None'].map(r => {
              const counts = {
                All:    result.findings.length,
                High:   summary?.high_risk   || 0,
                Medium: summary?.medium_risk || 0,
                Low:    summary?.low_risk    || 0,
                None:   summary?.no_risk     || 0,
              };
              return (
                <Button key={r} size="small"
                  variant={riskFilter === r ? 'contained' : 'outlined'}
                  color={r === 'High' ? 'error' : r === 'Medium' ? 'warning' : r === 'Low' ? 'success' : 'primary'}
                  onClick={() => setRiskFilter(r)}
                  sx={{ minWidth: 0, px: 1.5, fontSize: '0.72rem' }}>
                  {r} ({counts[r]})
                </Button>
              );
            })}
          </Box>

          {/* Findings table */}
          <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 2 }}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: '#f8fafc' }}>
                    {['Component', 'Type', 'Active', 'Updated', 'Flags', 'Risk', 'Summary', ''].map(h => (
                      <TableCell key={h} sx={{ fontWeight: 'bold', fontSize: '0.72rem', color: '#64748b', py: 1.2 }}>
                        {h}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredFindings.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} align="center" sx={{ py: 4, color: '#94a3b8' }}>
                        No findings match this filter.
                      </TableCell>
                    </TableRow>
                  ) : filteredFindings.map((finding, i) => {
                    const rc           = RISK_COLOR[finding.risk_level] || RISK_COLOR.None;
                    const wasDeactivated = deactivatedIds.has(finding.sys_id);
                    return (
                      <TableRow key={i} hover onClick={() => { setSelectedFinding(finding); setDialogOpen(true); }}
                        sx={{
                          cursor: 'pointer',
                          bgcolor: wasDeactivated ? '#f0fdf4' : i % 2 === 0 ? 'white' : '#fafafa',
                          '&:hover': { bgcolor: `${rc.bg} !important` },
                          borderLeft: `3px solid ${wasDeactivated ? '#16a34a' : rc.border}`,
                          opacity: wasDeactivated ? 0.75 : 1,
                        }}>

                        {/* Component name */}
                        <TableCell sx={{ maxWidth: 180 }}>
                          <Tooltip title={finding.name}>
                            <Typography variant="body2" fontWeight="medium" noWrap sx={{ maxWidth: 160 }}>
                              {finding.name}
                            </Typography>
                          </Tooltip>
                          <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#94a3b8', fontSize: 10 }}>
                            {finding.table_source}
                          </Typography>
                        </TableCell>

                        {/* Type */}
                        <TableCell>
                          <Chip label={finding.label} size="small" variant="outlined" sx={{ fontSize: '0.68rem' }} />
                        </TableCell>

                        {/* Active */}
                        <TableCell>
                          {(finding.active === 'true' || finding.active === true) && !wasDeactivated
                            ? <CheckCircleIcon sx={{ color: '#16a34a', fontSize: 16 }} />
                            : <HighlightOffIcon sx={{ color: '#94a3b8', fontSize: 16 }} />
                          }
                        </TableCell>

                        {/* Last updated */}
                        <TableCell>
                          <Typography variant="caption" color="text.secondary">
                            {finding.last_updated ? finding.last_updated.substring(0, 10) : '—'}
                          </Typography>
                        </TableCell>

                        {/* Flags */}
                        <TableCell sx={{ maxWidth: 180 }}>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.3 }}>
                            {finding.basic_flags?.slice(0, 2).map((f, fi) => (
                              <FlagBadgeDebt key={fi} flag={f} />
                            ))}
                            {finding.basic_flags?.length > 2 && (
                              <Chip label={`+${finding.basic_flags.length - 2}`} size="small"
                                sx={{ height: 20, fontSize: '0.68rem' }} />
                            )}
                          </Box>
                        </TableCell>

                        {/* Risk */}
                        <TableCell><RiskChip level={finding.risk_level} /></TableCell>

                        {/* AI Summary */}
                        <TableCell sx={{ maxWidth: 200 }}>
                          <Tooltip title={finding.ai_summary || ''}>
                            <Typography variant="caption" color="text.secondary" noWrap
                              sx={{ maxWidth: 190, display: 'block' }}>
                              {finding.ai_summary || '—'}
                            </Typography>
                          </Tooltip>
                        </TableCell>

                        {/* Action */}
                        <TableCell>
                          <Button size="small" variant="text"
                            endIcon={<OpenInNewIcon sx={{ fontSize: 13 }} />}
                            onClick={e => {
                              e.stopPropagation();
                              setSelectedFinding(finding);
                              setDialogOpen(true);
                            }}>
                            Details
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        </Box>
      )}

      

      {/* ── INTEGRATION findings table ── */}
      {intent === 'integration' && result?.findings?.length > 0 && (
        <Box>
          {/* Health bar */}
          {result.summary?.avg_score > 0 && (
            <Card elevation={0} sx={{ mb: 2, border: '1px solid #e2e8f0', borderRadius: 2 }}>
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" fontWeight="bold" color="text.secondary">
                    MODERNIZATION HEALTH
                  </Typography>
                  <Typography variant="caption" fontWeight="bold"
                    sx={{ color: scoreColor(result.summary.avg_score) }}>
                    {result.summary.avg_score}/100
                  </Typography>
                </Box>
                <LinearProgress variant="determinate" value={result.summary.avg_score}
                  sx={{ height: 8, borderRadius: 4, bgcolor: '#e2e8f0',
                    '& .MuiLinearProgress-bar': {
                      bgcolor: scoreColor(result.summary.avg_score), borderRadius: 4
                    }
                  }} />
              </CardContent>
            </Card>
          )}

          {/* Urgency filter */}
          <Box sx={{ display: 'flex', gap: 1, mb: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
            <FilterListIcon sx={{ color: '#94a3b8', fontSize: 18 }} />
            {['All', 'Critical', 'High', 'Medium', 'Low', 'None'].map(u => {
              const counts = {
                All:      result.findings.length,
                Critical: result.summary?.critical      || 0,
                High:     result.summary?.high          || 0,
                Medium:   result.summary?.medium        || 0,
                Low:      result.summary?.low           || 0,
                None:     result.summary?.already_modern || 0,
              };
              const uc = URGENCY_CFG[u] || URGENCY_CFG.None;
              return (
                <Button key={u} size="small"
                  variant={riskFilter === u ? 'contained' : 'outlined'}
                  onClick={() => setRiskFilter(u)}
                  sx={{
                    minWidth: 0, px: 1.5, fontSize: '0.72rem',
                    ...(riskFilter === u
                      ? { bgcolor: uc.bar, '&:hover': { bgcolor: uc.bar } }
                      : { color: uc.text, borderColor: uc.border })
                  }}>
                  {u} ({counts[u] ?? 0})
                </Button>
              );
            })}
          </Box>

          {/* Integration findings table */}
          <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 2 }}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: '#f8fafc' }}>
                    {['Integration Name', 'Type', 'Score', 'Urgency', 'Flags', 'Approach', ''].map(h => (
                      <TableCell key={h} sx={{ fontWeight: 'bold', fontSize: '0.72rem', color: '#64748b', py: 1.2 }}>
                        {h}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(result.findings.filter(f =>
                    riskFilter === 'All' ? true : f.urgency === riskFilter
                  )).length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 4, color: '#94a3b8' }}>
                        No findings match this filter.
                      </TableCell>
                    </TableRow>
                  ) : result.findings
                      .filter(f => riskFilter === 'All' ? true : f.urgency === riskFilter)
                      .map((f, i) => {
                        const uc = URGENCY_CFG[f.urgency] || URGENCY_CFG.None;
                        return (
                          <TableRow key={i} hover
                            onClick={() => { setSelectedFinding(f); setDialogOpen(true); }}
                            sx={{
                              cursor: 'pointer',
                              bgcolor: i % 2 === 0 ? 'white' : '#fafafa',
                              '&:hover': { bgcolor: `${uc.bg} !important` },
                              borderLeft: `3px solid ${uc.bar}`,
                            }}>

                            {/* Name */}
                            <TableCell sx={{ maxWidth: 180 }}>
                              <Tooltip title={f.name}>
                                <Typography variant="body2" fontWeight="medium" noWrap sx={{ maxWidth: 160 }}>
                                  {f.name}
                                </Typography>
                              </Tooltip>
                              <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#94a3b8', fontSize: 10 }}>
                                {f.table_source}
                              </Typography>
                            </TableCell>

                            {/* Type */}
                            <TableCell>
                              <Chip label={f.label} size="small" variant="outlined" sx={{ fontSize: '0.68rem' }} />
                            </TableCell>

                            {/* Score */}
                            <TableCell sx={{ minWidth: 90 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="body2" fontWeight="bold"
                                  sx={{ color: scoreColor(f.modernization_score), minWidth: 24 }}>
                                  {f.modernization_score}
                                </Typography>
                                <LinearProgress variant="determinate" value={f.modernization_score}
                                  sx={{ flex: 1, height: 5, borderRadius: 3, bgcolor: '#e2e8f0',
                                    '& .MuiLinearProgress-bar': {
                                      bgcolor: scoreColor(f.modernization_score), borderRadius: 3
                                    }
                                  }} />
                              </Box>
                            </TableCell>

                            {/* Urgency */}
                            <TableCell>
                              <Chip label={f.urgency || 'None'} size="small"
                                sx={{
                                  fontWeight: 'bold', fontSize: '0.72rem',
                                  bgcolor: uc.bg, color: uc.text,
                                  border: `1px solid ${uc.border}`,
                                }} />
                            </TableCell>

                            {/* Flags */}
                            <TableCell sx={{ maxWidth: 160 }}>
                              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.3 }}>
                                {f.basic_flags?.slice(0, 2).map((fl, fi) => (
                                  <FlagBadgeDebt key={fi} flag={fl} />
                                ))}
                                {f.basic_flags?.length > 2 && (
                                  <Chip label={`+${f.basic_flags.length - 2}`} size="small"
                                    sx={{ height: 20, fontSize: '0.68rem' }} />
                                )}
                              </Box>
                            </TableCell>

                            {/* Approach */}
                            <TableCell sx={{ maxWidth: 180 }}>
                              <Tooltip title={f.recommended_approach || ''}>
                                <Typography variant="caption" color="text.secondary" noWrap
                                  sx={{ maxWidth: 170, display: 'block' }}>
                                  {f.recommended_approach || '—'}
                                </Typography>
                              </Tooltip>
                            </TableCell>

                            {/* Action */}
                            <TableCell>
                              <Box sx={{ display: 'flex', gap: 0.5 }}>
                                <Button size="small" variant="text"
                                  endIcon={<OpenInNewIcon sx={{ fontSize: 13 }} />}
                                  onClick={e => {
                                    e.stopPropagation();
                                    setSelectedFinding(f);
                                    setDialogOpen(true);
                                  }}>
                                  Details
                                </Button>
                                {f.urgency !== 'None' && !modernizedIds.has(f.sys_id) && (
                                  <Button size="small" variant="outlined"
                                    onClick={e => {
                                      e.stopPropagation();
                                      setSelectedFinding(f);
                                      setModernizeOpen(true);
                                    }}
                                    sx={{
                                      fontSize: '0.68rem',
                                      color: '#7c3aed', borderColor: '#7c3aed',
                                      '&:hover': { bgcolor: '#faf5ff' }
                                    }}>
                                    Modernize
                                  </Button>
                                )}
                                {modernizedIds.has(f.sys_id) && (
                                  <Chip label="Modernized" size="small" color="success"
                                    sx={{ height: 20, fontSize: '0.65rem' }} />
                                )}
                              </Box>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        </Box>
      )}
{/* ── Release result ── */}
      {/* Release payload supports nested readiness or flattened top-level fields */}
      {isRelease && releaseData && (
        <Box>
          {/* Stat cards */}
          {/* <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
            {[
              {
                label: 'Production Readiness',
                value: releaseData.production_readiness,
                color: releaseData.production_readiness?.toLowerCase().includes('ready') ? '#16a34a' : '#dc2626'
              },
              {
                label: 'Risk Score',
                value: releaseData.risk_score,
                color: releaseData.risk_score === 'High' ? '#dc2626'
                    : releaseData.risk_score === 'Medium' ? '#d97706' : '#16a34a'
              },
            ].map(r => (
              <Paper key={r.label} elevation={0} sx={{
                border: `1px solid ${r.color}40`, borderTop: `3px solid ${r.color}`,
                borderRadius: 2, px: 3, py: 1.5, minWidth: 160,
              }}>
                <Typography variant="caption" color="text.secondary">{r.label}</Typography>
                <Typography variant="h6" fontWeight="bold" sx={{ color: r.color }}>
                  {r.value || '—'}
                </Typography>
              </Paper>
            ))}
          </Box> */}

          {/* CAB Summary */}
          {releaseData.cab_summary && (
            <Paper elevation={0} sx={{
              p: 2, mb: 2, bgcolor: '#f8fafc',
              border: '1px solid #e2e8f0', borderRadius: 2,
            }}>
              <Typography variant="caption" fontWeight="bold" color="text.secondary"
                sx={{ display: 'block', mb: 0.5 }}>
                CAB SUMMARY
              </Typography>
              <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
                {releaseData.cab_summary}
              </Typography>
            </Paper>
          )}

          {/* Issues Found */}
          {releaseData.issues_found?.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" fontWeight="bold" color="text.secondary"
                sx={{ display: 'block', mb: 1 }}>
                ISSUES FOUND
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8 }}>
                {releaseData.issues_found.map((issue, i) => (
                  <Paper key={i} elevation={0} sx={{
                    px: 2, py: 1, bgcolor: '#fef2f2',
                    border: '1px solid #fca5a5', borderRadius: 2,
                  }}>
                    <Typography variant="body2" color="#dc2626">• {issue}</Typography>
                  </Paper>
                ))}
              </Box>
            </Box>
          )}

          {/* Recommended Actions + Rollback side by side */}
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {releaseData.recommended_actions?.length > 0 && (
              <Paper elevation={0} sx={{
                flex: 1, minWidth: 200, p: 2,
                border: '1px solid #e2e8f0', borderRadius: 2,
              }}>
                <Typography variant="caption" fontWeight="bold" color="text.secondary"
                  sx={{ display: 'block', mb: 1 }}>
                  RECOMMENDED ACTIONS
                </Typography>
                <Box component="ul" sx={{ pl: 2, m: 0 }}>
                  {releaseData.recommended_actions.map((act, i) => (
                    <li key={i}>
                      <Typography variant="body2" sx={{ mb: 0.5 }}>{act}</Typography>
                    </li>
                  ))}
                </Box>
              </Paper>
            )}

            {releaseData.rollback_suggestions && (
              <Paper elevation={0} sx={{
                flex: 1, minWidth: 200, p: 2,
                bgcolor: '#f0fdf4', border: '1px solid #86efac', borderRadius: 2,
              }}>
                <Typography variant="caption" fontWeight="bold" color="text.secondary"
                  sx={{ display: 'block', mb: 1 }}>
                  ROLLBACK STRATEGY
                </Typography>
                <Typography variant="body2" color="#16a34a">
                  {releaseData.rollback_suggestions}
                </Typography>
              </Paper>
            )}
          </Box>

          {/* Change number + table badge */}
          {releaseData.change_number && (
            <Box sx={{ mt: 1.5, display: 'flex', gap: 1 }}>
              <Paper elevation={0} sx={{
                px: 1.5, py: 0.5, border: '1px solid #e2e8f0',
                borderRadius: 2, display: 'inline-flex', gap: 1, alignItems: 'center',
              }}>
                <Typography variant="caption" color="text.secondary">Change:</Typography>
                <Typography variant="body2" fontWeight="bold" sx={{ fontFamily: 'monospace' }}>
                  {releaseData.change_number}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>Table:</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: 11, color: '#64748b' }}>
                  {releaseData.table}
                </Typography>
              </Paper>
            </Box>
          )}
        </Box>
      )}
      {/* ── Release result ── */}
      {isRelease && result?.readiness && (
        <Box>
          {/* Stat cards */}
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
            {[
              {
                label: 'Production Readiness',
                value: result.readiness.production_readiness,
                color: result.readiness.production_readiness?.toLowerCase().includes('ready') ? '#16a34a' : '#dc2626'
              },
              {
                label: 'Risk Score',
                value: result.readiness.risk_score,
                color: result.readiness.risk_score === 'High' ? '#dc2626'
                    : result.readiness.risk_score === 'Medium' ? '#d97706' : '#16a34a'
              },
            ].map(r => (
              <Paper key={r.label} elevation={0} sx={{
                border: `1px solid ${r.color}40`, borderTop: `3px solid ${r.color}`,
                borderRadius: 2, px: 3, py: 1.5, minWidth: 160,
              }}>
                <Typography variant="caption" color="text.secondary">{r.label}</Typography>
                <Typography variant="h6" fontWeight="bold" sx={{ color: r.color }}>
                  {r.value || '—'}
                </Typography>
              </Paper>
            ))}
          </Box>

          {/* CAB Summary */}
          {result.readiness.cab_summary && (
            <Paper elevation={0} sx={{
              p: 2, mb: 2, bgcolor: '#f8fafc',
              border: '1px solid #e2e8f0', borderRadius: 2,
            }}>
              <Typography variant="caption" fontWeight="bold" color="text.secondary"
                sx={{ display: 'block', mb: 0.5 }}>
                CAB SUMMARY
              </Typography>
              <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
                {result.readiness.cab_summary}
              </Typography>
            </Paper>
          )}

          {/* Issues Found */}
          {result.readiness.issues_found?.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" fontWeight="bold" color="text.secondary"
                sx={{ display: 'block', mb: 1 }}>
                ISSUES FOUND
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8 }}>
                {result.readiness.issues_found.map((issue, i) => (
                  <Paper key={i} elevation={0} sx={{
                    px: 2, py: 1, bgcolor: '#fef2f2',
                    border: '1px solid #fca5a5', borderRadius: 2,
                  }}>
                    <Typography variant="body2" color="#dc2626">• {issue}</Typography>
                  </Paper>
                ))}
              </Box>
            </Box>
          )}

          {/* Recommended Actions + Rollback side by side */}
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {result.readiness.recommended_actions?.length > 0 && (
              <Paper elevation={0} sx={{
                flex: 1, minWidth: 200, p: 2,
                border: '1px solid #e2e8f0', borderRadius: 2,
              }}>
                <Typography variant="caption" fontWeight="bold" color="text.secondary"
                  sx={{ display: 'block', mb: 1 }}>
                  RECOMMENDED ACTIONS
                </Typography>
                <Box component="ul" sx={{ pl: 2, m: 0 }}>
                  {result.readiness.recommended_actions.map((act, i) => (
                    <li key={i}>
                      <Typography variant="body2" sx={{ mb: 0.5 }}>{act}</Typography>
                    </li>
                  ))}
                </Box>
              </Paper>
            )}

            {result.readiness.rollback_suggestions && (
              <Paper elevation={0} sx={{
                flex: 1, minWidth: 200, p: 2,
                bgcolor: '#f0fdf4', border: '1px solid #86efac', borderRadius: 2,
              }}>
                <Typography variant="caption" fontWeight="bold" color="text.secondary"
                  sx={{ display: 'block', mb: 1 }}>
                  ROLLBACK STRATEGY
                </Typography>
                <Typography variant="body2" color="#16a34a">
                  {result.readiness.rollback_suggestions}
                </Typography>
              </Paper>
            )}
          </Box>

          {/* Change number + table badge */}
          {result.change_number && (
            <Box sx={{ mt: 1.5, display: 'flex', gap: 1 }}>
              <Paper elevation={0} sx={{
                px: 1.5, py: 0.5, border: '1px solid #e2e8f0',
                borderRadius: 2, display: 'inline-flex', gap: 1, alignItems: 'center',
              }}>
                <Typography variant="caption" color="text.secondary">Change:</Typography>
                <Typography variant="body2" fontWeight="bold" sx={{ fontFamily: 'monospace' }}>
                  {result.change_number}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>Table:</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: 11, color: '#64748b' }}>
                  {result.table}
                </Typography>
              </Paper>
            </Box>
          )}
        </Box>
      )}

      {/* ── Raw JSON toggle ── */}
      {/* <Typography variant="caption"
        sx={{ color: '#94a3b8', cursor: 'pointer', mt: 1.5, display: 'inline-block',
              '&:hover': { color: '#475569' } }}
        onClick={() => {
          const el = document.getElementById(`raw-${intent}`);
          if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
        }}>
        View raw output ▾
      </Typography>
      <Paper id={`raw-${intent}`} elevation={0}
        sx={{ display: 'none', mt: 1, p: 2, bgcolor: '#1e293b', borderRadius: 2,
              overflowX: 'auto', maxHeight: 280 }}>
        <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: 11, color: '#a6e22e' }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      </Paper> */}

      {/* ── Finding detail dialog ── */}
       <AgentFindingDetailDialog
        finding={selectedFinding}
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onDeactivated={handleDeactivated}
        onModernizeClick={
          selectedFinding?.urgency && selectedFinding.urgency !== 'None'
            ? () => setModernizeOpen(true)
            : undefined
        }
      />

      {/* ── Modernize dialog (integration only) ── */}
      <ModernizeDialog
        finding={selectedFinding}
        open={modernizeOpen}
        onClose={() => setModernizeOpen(false)}
        onApplied={handleApplied}
      />
    </Box>
  );
}


// function ValidatorToggle({ blueprint, validateEndpoint, onConfirmed, buildLoading, selectedFeatures }) {
//   const [open, setOpen] = useState(false);
 
//   return (
//     <Box>
//       <Button
//         size="small"
//         variant="outlined"
//         onClick={() => setOpen(prev => !prev)}
//         sx={{
//           mb: open ? 2 : 0,
//           borderColor: '#6366f1',
//           color: '#6366f1',
//           fontSize: '0.75rem',
//           '&:hover': { bgcolor: '#eef2ff' },
//         }}
//         startIcon={open ? '▲' : '▼'}
//       >
//         {open ? 'Hide Validation Tests' : 'Run Validation & Deploy'}
//       </Button>
 
//       {open && (
//         <BlueprintValidator
//           blueprint={blueprint}
//           validateEndpoint={validateEndpoint}
//           onConfirmed={onConfirmed}
//           buildLoading={buildLoading}
//           selectedFeatures={selectedFeatures}    // ← ADD THIS LINE
//         />
//       )}
//     </Box>
//   );
// }

// ── Single agent message bubble ───────────────────────────────────────────────




function AgentBubble({ msg }) {
  const { routing, prescan, progress, result, clarify, error } = msg;
  const cfg = routing ? (INTENT_CFG[routing.intent] || {}) : {};
 
  // ── local state for the full new_module flow ──────────────────────────────
  const [agentPhase,       setAgentPhase]       = useState('idle');
  // idle → discovering → feature_select → generating → validating → result
 
  const [moduleName,       setModuleName]       = useState('');
  const [selectedFeatures, setSelectedFeatures] = useState([]);
  const [blueprint,        setBlueprint]        = useState(null);
  const [buildLoading,     setBuildLoading]     = useState(false);
  const [buildResult,      setBuildResult]      = useState(null);
  const [buildError,       setBuildError]       = useState(null);
 
  // scoped_app keeps the original simple flow
  const [scopedBlueprint,  setScopedBlueprint]  = useState(null);
 
  const isBuildIntent  = ['new_module', 'scoped_app'].includes(routing?.intent);
  const isNewModule    = routing?.intent === 'new_module';
  const isScopedApp    = routing?.intent === 'scoped_app';
 
  // ── When result arrives, start the appropriate flow ───────────────────────
  useEffect(() => {
    if (!result || !isBuildIntent || buildResult) return;
 
    if (isNewModule) {
      // For new_module: start discovery flow instead of showing blueprint directly
      // Extract a clean module name from the result or the routing
      const name = result.module_name || result.app_name || '';
      setModuleName(name);
      setAgentPhase('discovering');
    } else if (isScopedApp) {
      // Scoped app: keep original flow — show blueprint then validate
      setScopedBlueprint(result);
      setAgentPhase('validating');
    }
  }, [result, isBuildIntent]);
 
  // ── New Module: user selected features → generate partial blueprint ───────
  const handleFeaturesSelected = async (features) => {
    setSelectedFeatures(features);
    setAgentPhase('generating');
    setBuildError(null);
    setBlueprint(null);
 
    // Get the original user prompt from the message (stored in routing.prompt if available)
    const originalPrompt = routing?.original_prompt || moduleName;
 
    try {
      const response = await fetch(`${API_BASE}/api/generate-blueprint`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          prompt:            originalPrompt,
          selected_features: features,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Blueprint generation failed');
      if (!data.blueprint) throw new Error('No blueprint returned from backend');
 
      setBlueprint(data.blueprint);
      setAgentPhase('validating');
    } catch (err) {
      setBuildError(err.message);
      setAgentPhase('feature_select');
    }
  };
 
  // ── Push blueprint to ServiceNow ─────────────────────────────────────────
  // const handleBuild = async () => {
  //   const bp       = blueprint || scopedBlueprint;
  //   const endpoint = isScopedApp
  //     ? '/api/build-scoped-from-blueprint'
  //     : '/api/build-from-blueprint';
 
  //   if (!bp) return;
  //   setBuildLoading(true);
  //   setBuildError(null);
 
  //   try {
  //     const response = await fetch(`${API_BASE}${endpoint}`, {
  //       method:  'POST',
  //       headers: { 'Content-Type': 'application/json' },
  //       body:    JSON.stringify({ blueprint: bp }),
  //     });
  //     if (!response.ok) throw new Error('Build failed');
  //     const data = await response.json();
  //     setBuildResult(data.data);
  //     setAgentPhase('result');
  //   } catch (err) {
  //     setBuildError(err.message);
  //   } finally {
  //     setBuildLoading(false);
  //   }
  // };

  const handleBuild = async () => {
    const bp = blueprint || scopedBlueprint;
    if (!bp) return;
 
    setBuildLoading(true);
    setBuildError(null);
 
    const endpoint = isScopedApp
      ? '/api/build-scoped-from-blueprint'
      : '/api/build-and-test';        // ← uses new combined endpoint
 
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          blueprint:         bp,
          module_name:       bp.module_name || bp.app_name || moduleName,
          selected_features: selectedFeatures,
        }),
      });
      if (!response.ok) throw new Error('Build failed');
      const data = await response.json();
      setBuildResult(data);           // ← now contains build_result + atf
      setAgentPhase('result');
    } catch (err) {
      setBuildError(err.message);
    } finally {
      setBuildLoading(false);
    }
  };
 
  return (
    <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start', mb: 2 }}>
      <Avatar sx={{ width: 34, height: 34, bgcolor: '#6366f1', fontSize: 14, fontWeight: 700, flexShrink: 0 }}>
        AI
      </Avatar>
 
      <Box sx={{ flex: 1, minWidth: 0 }}>
 
        {/* Routing badge */}
        {routing && (
          <Chip
            icon={cfg.icon}
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <span>{cfg.label || routing.label}</span>
                <Typography variant="caption" sx={{ opacity: 0.65 }}>
                  {Math.round(routing.confidence * 100)}% match
                </Typography>
              </Box>
            }
            sx={{
              mb: 1.5, bgcolor: cfg.bg, border: `1px solid ${cfg.color}40`,
              color: cfg.color, fontWeight: 600,
              '& .MuiChip-icon': { color: cfg.color }, height: 32,
            }}
          />
        )}
 
        {/* Progress bar */}
        {progress && (
          <Card elevation={0} sx={{ mb: 1.5, border: '1px solid #e2e8f0', borderRadius: 2 }}>
            <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="caption" color="text.secondary">Analysing records…</Typography>
                <Typography variant="caption" fontWeight="bold" color="primary">
                  {progress.done} / {progress.total}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={progress.total > 0 ? (progress.done / progress.total) * 100 : 0}
                sx={{ height: 6, borderRadius: 4,
                  '& .MuiLinearProgress-bar': { borderRadius: 4, bgcolor: cfg.color || '#6366f1' } }}
              />
            </CardContent>
          </Card>
        )}
 
        {/* Typing dots — while waiting for first event */}
        {!routing && !error && !clarify && <TypingDots />}
 
        {/* ══════════════════════════════════════════════════════════════
            NEW MODULE FLOW — 5 phases
            ══════════════════════════════════════════════════════════ */}
        {result && isNewModule && (
          <Box>
 
            {/* Phase: discovering / feature_select */}
            {(agentPhase === 'discovering' || agentPhase === 'feature_select') && moduleName && (
              <DiscoveryPanel
                moduleName={moduleName}
                onFeaturesSelected={handleFeaturesSelected}
                onCancel={() => setAgentPhase('idle')}
              />
            )}
 
            {/* Phase: generating partial blueprint */}
            {agentPhase === 'generating' && (
              <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 2, p: 3, textAlign: 'center' }}>
                <CircularProgress size={36} sx={{ mb: 1.5, color: '#6366f1' }} />
                <Typography variant="body1" fontWeight="medium" color="text.secondary">
                  Generating blueprint for {selectedFeatures.length} feature{selectedFeatures.length !== 1 ? 's' : ''}...
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {selectedFeatures.map(f => f.replace(/_/g, ' ')).join(', ')}
                </Typography>
              </Card>
            )}
 
            {/* Phase: validating — show full blueprint preview + validator */}
            {/* {agentPhase === 'validating' && blueprint && (
              <Box>
                <Card elevation={0} sx={{ mb: 2, border: '1px solid #e2e8f0', borderRadius: 2 }}>
                  <CardContent sx={{ p: 2.5 }}>
                    <BlueprintPreview
                      blueprint={blueprint}
                      selectedFeatures={selectedFeatures}
                    />
                  </CardContent>
                </Card>
 
                <ValidatorToggle
                  blueprint={blueprint}
                  validateEndpoint="/api/validate-module"
                  onConfirmed={handleBuild}
                  buildLoading={buildLoading}
                  selectedFeatures={selectedFeatures} 
                />
 
                {buildError && (
                  <Alert severity="error" sx={{ mt: 2 }}>{buildError}</Alert>
                )}
              </Box>
            )} */}

            {/* Phase: validating — show blueprint + Deploy button */}
            {agentPhase === 'validating' && blueprint && (
              <Box>
                <Card elevation={0} sx={{ mb: 2, border: '1px solid #e2e8f0', borderRadius: 2 }}>
                  <CardContent sx={{ p: 2.5 }}>
                    <BlueprintPreview
                      blueprint={blueprint}
                      selectedFeatures={selectedFeatures}
                    />
                  </CardContent>
                </Card>
 
                {buildError && (
                  <Alert severity="error" sx={{ mb: 2 }}>{buildError}</Alert>
                )}
 
                {/* Deploy & Generate Tests button */}
                <Button
                  variant="contained"
                  size="large"
                  startIcon={buildLoading
                    ? <CircularProgress size={18} color="inherit" />
                    : <ScienceIcon />}
                  onClick={handleBuild}
                  disabled={buildLoading}
                  sx={{
                    bgcolor: '#6366f1',
                    '&:hover': { bgcolor: '#4f46e5' },
                    px: 4,
                  }}
                >
                  {buildLoading ? 'Creating in ServiceNow...' : 'Add into ServiceNow & Generate ATF Tests'}
                </Button>
              </Box>
            )}
 
            {/* Phase: result — show build result + ATF */}
            {agentPhase === 'result' && buildResult && (
              <Box>
                <ResultBlock
                  result={buildResult.build_result || buildResult}
                  intent={routing?.intent}
                />
                {buildResult.atf && (
                  <Box sx={{ mt: 2 }}>
                    <ATFResults
                      atf={buildResult.atf}
                      moduleName={moduleName}
                      snowInstance="https://abhrademo5.service-now.com"
                    />
                  </Box>
                )}
              </Box>
            )}
          </Box>
        )}
 
        {/* ══════════════════════════════════════════════════════════════
            SCOPED APP FLOW — original simple flow (no discovery needed)
            ══════════════════════════════════════════════════════════ */}
        {result && isScopedApp && (
          <Box>
            {/* Blueprint preview before validation */}
            {agentPhase === 'validating' && scopedBlueprint && !buildResult && (
              <Box>
                <Card elevation={0} sx={{ mb: 2, border: '1px solid #e2e8f0', borderRadius: 2 }}>
                  <CardContent sx={{ p: 2.5 }}>
                    <Box sx={{ pl: 1, borderLeft: `4px solid ${cfg.color || '#22c55e'}`, mb: 1.5 }}>
                      <Typography variant="h6" fontWeight="bold">
                        {scopedBlueprint.app_name || scopedBlueprint.module_name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {scopedBlueprint.description}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 0.8, flexWrap: 'wrap' }}>
                      {[
                        { label: 'Tables',    value: scopedBlueprint.tables?.length    || 0, color: '#3b82f6' },
                        { label: 'Roles',     value: scopedBlueprint.roles?.length     || 0, color: '#f59e0b' },
                        { label: 'Workflows', value: scopedBlueprint.workflows?.length || 0, color: '#10b981' },
                        { label: 'Forms',     value: scopedBlueprint.forms?.length     || 0, color: '#8b5cf6' },
                      ].filter(s => s.value > 0).map(s => (
                        <Chip key={s.label}
                          label={`${s.value} ${s.label}`} size="small"
                          sx={{ bgcolor: `${s.color}15`, color: s.color,
                                border: `1px solid ${s.color}40`, fontWeight: 'bold' }} />
                      ))}
                    </Box>
                  </CardContent>
                </Card>
 
                <Button
                  variant="contained"
                  size="large"
                  startIcon={buildLoading
                    ? <CircularProgress size={18} color="inherit" />
                    : <CloudUploadIcon />}
                  onClick={handleBuild}
                  disabled={buildLoading}
                  sx={{
                    bgcolor: '#22c55e',
                    '&:hover': { bgcolor: '#16a34a' },
                    px: 4,
                  }}
                >
                  {buildLoading ? 'Adding to ServiceNow...' : 'Add into ServiceNow'}
                </Button>
 
                {buildError && (
                  <Alert severity="error" sx={{ mt: 2 }}>{buildError}</Alert>
                )}
              </Box>
            )}
 
            {/* After successful build */}
            {buildResult && (
              <ResultBlock result={buildResult} intent={routing?.intent} />
            )}
          </Box>
        )}
 
        {/* NON-BUILD intents — show result directly */}
        {result && routing && !isBuildIntent && (
          <ResultBlock result={result} intent={routing.intent} />
        )}
 
        {/* Clarification */}
        {clarify && (
          <Alert severity="info" icon={<HelpOutlineIcon />} sx={{ borderRadius: 2 }}>
            {clarify}
          </Alert>
        )}
 
        {/* Error */}
        {error && (
          <Alert severity="error" icon={<ErrorOutlineIcon />} sx={{ borderRadius: 2 }}>
            {error}
          </Alert>
        )}
      </Box>
    </Box>
  );
}

// ── User message bubble ────────────────────────────────────────────────────────
function UserBubble({ text }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
      <Paper elevation={0} sx={{
        px: 2, py: 1.2, bgcolor: '#1e293b', color: '#f8fafc',
        borderRadius: '18px 18px 4px 18px',
        maxWidth: '72%', fontSize: 14, lineHeight: 1.5,
        whiteSpace: 'pre-wrap', wordBreak: 'break-word',
      }}>
        {text}
      </Paper>
    </Box>
  );
}

// ── Placeholder when chat is empty ────────────────────────────────────────────
function EmptyState({ onSelect }) {
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column',
               alignItems: 'center', justifyContent: 'center', py: 6, px: 2 }}>
      <Avatar sx={{ width: 64, height: 64, bgcolor: '#6366f1', mb: 2 }}>
        <SmartToyIcon sx={{ fontSize: 34 }} />
      </Avatar>
      <Typography variant="h6" fontWeight="bold" sx={{ mb: 0.5 }}>
        ServiceNow AI Agent
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center', maxWidth: 420 }}>
        Describe any requirement — the agent will automatically identify the right
        worker and execute it. No tool selection needed.
      </Typography>
      <Divider sx={{ width: '100%', maxWidth: 500, mb: 2 }} />
      <Typography variant="overline" color="text.secondary" sx={{ mb: 1.5 }}>
        Try one of these
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, width: '100%', maxWidth: 500 }}>
        {EXAMPLES.map((ex, i) => (
          <Paper
            key={i}
            elevation={0}
            onClick={() => onSelect(ex)}
            sx={{
              px: 2, py: 1.2, border: '1px solid #e2e8f0', borderRadius: 2,
              cursor: 'pointer', fontSize: 14, color: '#475569',
              transition: 'all 0.15s',
              '&:hover': { borderColor: '#6366f1', bgcolor: '#eef2ff', color: '#4338ca' },
            }}
          >
            {ex}
          </Paper>
        ))}
      </Box>
    </Box>
  );
}

// ── Main AgentChat component ──────────────────────────────────────────────────
export default function AgentChat() {
  const [messages, setMessages] = useState([]);
  const [input,    setInput]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const bottomRef               = useRef(null);
  const abortRef                = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMsg   = (msg)        => setMessages(prev => [...prev, msg]);
  const patchMsg = (id, patch)  =>
    setMessages(prev => prev.map(m => m.id === id ? { ...m, ...patch } : m));

  const send = useCallback(async () => {
    const prompt = input.trim();
    if (!prompt || loading) return;

    setInput('');
    setLoading(true);
    addMsg({ id: Date.now(), role: 'user', text: prompt });

    const agentId = Date.now() + 1;
    addMsg({
      id: agentId, role: 'agent',
      routing: null, prescan: null, progress: null,
      result: null,  clarify: null, error: null,
    });

    abortRef.current?.abort();
    const controller  = new AbortController();
    abortRef.current  = controller;

    try {
      const res = await fetch(`${API_BASE}/api/agent`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ prompt, session_id: SESSION_ID }),
        signal:  controller.signal,
      });

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const raw = decoder.decode(value, { stream: true });
        for (const line of raw.split('\n')) {
          const trimmed = line.replace(/^data:\s*/, '').trim();
          if (!trimmed) continue;
          let chunk;
          try { chunk = JSON.parse(trimmed); } catch { continue; }

          switch (chunk.type) {
            case 'routing':
              patchMsg(agentId, { routing: chunk });
              break;
            case 'prescan':
              patchMsg(agentId, { prescan: chunk.summary });
              break;
            case 'progress':
              setMessages(prev => prev.map(m => {
                if (m.id !== agentId) return m;
                const ex = m.progress || { done: 0, total: 0 };
                return { ...m, progress: { done: chunk.done, total: chunk.total } };
              }));
              break;
            case 'result':
              patchMsg(agentId, { result: chunk.data });
              break;
            case 'clarify':
              patchMsg(agentId, { clarify: chunk.question });
              break;
            case 'error':
              patchMsg(agentId, { error: chunk.message });
              break;
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError')
        patchMsg(agentId, { error: err.message });
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <Box sx={{
      display: 'flex', flexDirection: 'column',
      height: 'calc(100vh - 112px)',   // accounts for AppBar (64px) + parent padding (mt:8 = 48px)
      animation: 'fadeIn 0.4s ease-in',
    }}>

      {/* ── Message list ── */}
      <Box sx={{ flex: 1, overflowY: 'auto', px: 1, pt: 1 }}>
        {messages.length === 0
          ? <EmptyState onSelect={setInput} />
          : messages.map(msg =>
              msg.role === 'user'
                ? <UserBubble  key={msg.id} text={msg.text} />
                : <AgentBubble key={msg.id} msg={msg} />
            )
        }
        <div ref={bottomRef} />
      </Box>

      {/* ── Input bar ── */}
      <Card elevation={0} sx={{
        mt: 1.5, border: '1px solid #e2e8f0', borderRadius: 3,
        flexShrink: 0,
      }}>
        <CardContent sx={{ p: '12px 16px !important' }}>
          <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-end' }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              size="small"
              placeholder="Describe your requirement… e.g. Scan for unused business rules, Create a REST integration for JIRA"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKey}
              disabled={loading}
              sx={{
                '& .MuiOutlinedInput-root': { borderRadius: 2.5 },
              }}
            />
            <Button
              variant="contained"
              onClick={send}
              disabled={loading || !input.trim()}
              sx={{
                minWidth: 48, width: 48, height: 40,
                borderRadius: 2.5, p: 0, flexShrink: 0,
                bgcolor: '#6366f1', '&:hover': { bgcolor: '#4f46e5' },
              }}
            >
              {loading
                ? <CircularProgress size={18} color="inherit" />
                : <SendIcon sx={{ fontSize: 18 }} />
              }
            </Button>
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
            Press Enter to send · Shift+Enter for new line
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}