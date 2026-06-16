import React, { useState, useEffect } from 'react';
import {
  Container, Box, Typography, TextField, Button, Card, CardContent,
  Grid, Accordion, AccordionSummary, AccordionDetails, CircularProgress,
  Alert, Chip, Divider, Paper, Drawer, List, ListItem, ListItemButton,
  ListItemIcon, ListItemText, AppBar, Toolbar, CssBaseline, LinearProgress,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions, FormControlLabel,
  Checkbox, FormGroup, Tooltip, Badge, Stack
} from '@mui/material';

// Add these to your top icon imports
import AltRouteIcon from '@mui/icons-material/AltRoute';
import PlaylistAddCheckIcon from '@mui/icons-material/PlaylistAddCheck';
import AnnouncementIcon from '@mui/icons-material/Announcement';
import PublishedWithChangesIcon from '@mui/icons-material/PublishedWithChanges';
import BlockIcon from '@mui/icons-material/Block';
import ReleaseChangeTool from './ReleasechangeTools';
// ADD after the ReleaseChangeTool import line
import AgentChat from './AgentChat';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import IntegrationTool from './IntegrationTool';

// Icons for the Sidebar
import AddBoxIcon from '@mui/icons-material/AddBox';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import SyncAltIcon from '@mui/icons-material/SyncAlt';
import CleaningServicesIcon from '@mui/icons-material/CleaningServices';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import StorageIcon from '@mui/icons-material/Storage';

// Icons for the Results Dashboard
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import TableChartIcon from '@mui/icons-material/TableChart';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import SecurityIcon from '@mui/icons-material/Security';
import EmailIcon from '@mui/icons-material/Email';
import FactCheckIcon from '@mui/icons-material/FactCheck';

// Icons for Tech Debt
import BugReportIcon from '@mui/icons-material/BugReport';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutlined';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutlined';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import FilterListIcon from '@mui/icons-material/FilterList';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import CodeIcon from '@mui/icons-material/Code';
import FlagIcon from '@mui/icons-material/Flag';
import RecommendIcon from '@mui/icons-material/Recommend';
import HighlightOffIcon from '@mui/icons-material/HighlightOff';

// import BlueprintValidator from './BlueprintValidator';
import DiscoveryPanel from './DiscoveryPanel';

const drawerWidth = 280;
const API_BASE = 'http://127.0.0.1:8000';

// ─────────────────────────────────────────
// RISK LEVEL HELPERS
// ─────────────────────────────────────────
const RISK_COLOR = {
  High:   { bg: '#fef2f2', border: '#fca5a5', text: '#dc2626', chip: 'error'   },
  Medium: { bg: '#fffbeb', border: '#fcd34d', text: '#d97706', chip: 'warning' },
  Low:    { bg: '#f0fdf4', border: '#86efac', text: '#16a34a', chip: 'success' },
  None:   { bg: '#f8fafc', border: '#cbd5e1', text: '#64748b', chip: 'default' },
};

const RiskChip = ({ level }) => {
  const cfg = RISK_COLOR[level] || RISK_COLOR.None;
  const icons = { High: <ErrorOutlineIcon />, Medium: <WarningAmberIcon />, Low: <InfoOutlinedIcon />, None: <CheckCircleOutlineIcon /> };
  return (
    <Chip
      icon={icons[level] || icons.None}
      label={level || 'None'}
      size="small"
      color={cfg.chip}
      variant="filled"
      sx={{ fontWeight: 'bold', fontSize: '0.75rem' }}
    />
  );
};

// ─────────────────────────────────────────
// FLAG BADGE
// ─────────────────────────────────────────
const FlagBadge = ({ flag }) => {
  const color =
    flag.includes('eval') || flag.includes('sleep') || flag.includes('hardcoded') ? '#dc2626'
    : flag.includes('inactive') || flag.includes('stale') ? '#d97706'
    : '#64748b';
  return (
    <Chip
      label={flag}
      size="small"
      sx={{
        fontFamily: 'monospace', fontSize: '0.7rem',
        bgcolor: `${color}15`, color, border: `1px solid ${color}40`,
        height: 22
      }}
    />
  );
};

// ─────────────────────────────────────────
// SUMMARY STAT CARD
// ─────────────────────────────────────────
const StatCard = ({ label, value, color, icon }) => (
  <Card elevation={0} sx={{ border: `1px solid ${color}40`, borderTop: `4px solid ${color}`, borderRadius: 2, flex: 1 }}>
    <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="h3" fontWeight="bold" sx={{ color, lineHeight: 1 }}>{value}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{label}</Typography>
        </Box>
        <Box sx={{ color, opacity: 0.6, mt: 0.5 }}>{icon}</Box>
      </Box>
    </CardContent>
  </Card>
);

// ─────────────────────────────────────────
// TABLES WHERE DEACTIVATE IS BLOCKED (mirrors backend)
// ─────────────────────────────────────────
const DEACTIVATE_BLOCKED_TABLES = new Set([
  'sys_security_acl',
  'sys_dictionary',
  'sys_db_object',
  'sys_properties',
]);

// ─────────────────────────────────────────
// FINDING DETAIL DIALOG  (with Deactivate)
// ─────────────────────────────────────────
function FindingDetailDialog({ finding, open, onClose, onDeactivated }) {
  const [confirmOpen,       setConfirmOpen]       = useState(false);
  const [deactivating,      setDeactivating]      = useState(false);
  const [deactivateResult,  setDeactivateResult]  = useState(null); // {success, message}
  const [isActive,          setIsActive]          = useState(null); // live active state

  // Sync isActive whenever the dialog opens with a new finding
  useEffect(() => {
    if (finding) {
      setIsActive(finding.active === 'true' || finding.active === true);
      setDeactivateResult(null);
    }
  }, [finding]);

  if (!finding) return null;
  const riskCfg = RISK_COLOR[finding.risk_level] || RISK_COLOR.None;

  // Should the Deactivate button be shown?
  const canDeactivate =
    isActive &&                                          // record is currently active
    !DEACTIVATE_BLOCKED_TABLES.has(finding.table_source) && // not a protected table
    (finding.risk_level === 'High' || finding.risk_level === 'Medium' || finding.risk_level === 'Low');

  // ── DEACTIVATE HANDLER ───────────────────
  const handleDeactivate = async () => {
    setConfirmOpen(false);
    setDeactivating(true);
    setDeactivateResult(null);

    try {
      const response = await fetch(`${API_BASE}/api/deactivate-record`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table:  finding.table_source,
          sys_id: finding.sys_id,
          name:   finding.name,
        }),
      });
      const data = await response.json();

      if (data.status === 'success') {
        setIsActive(false);
        setDeactivateResult({ success: true, message: data.message });
        // Notify parent (TechDebtTool) to update the findings table row
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
      {/* ── MAIN DETAIL DIALOG ── */}
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
            {/* Live active badge */}
            <Chip
              size="small"
              label={isActive ? 'Active' : 'Inactive'}
              icon={isActive ? <CheckCircleOutlineIcon /> : <HighlightOffIcon />}
              color={isActive ? 'success' : 'default'}
              variant="outlined"
            />
          </Box>
        </DialogTitle>

        <DialogContent sx={{ pt: 3 }}>
          {/* Deactivate result banner */}
          {deactivateResult && (
            <Alert
              severity={deactivateResult.success ? 'success' : 'error'}
              sx={{ mb: 2 }}
              onClose={() => setDeactivateResult(null)}
            >
              {deactivateResult.success
                ? `✅ ${deactivateResult.message} — Record is now inactive in ServiceNow. Re-activate anytime from the record.`
                : `❌ ${deactivateResult.message}`}
            </Alert>
          )}

          <Grid container spacing={3}>
            {/* Metadata */}
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>METADATA</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8 }}>
                {[
                  ['Active',       isActive ? '✅ Yes' : '❌ No (Inactive)'],
                  ['Last Updated', finding.last_updated || '—'],
                  ['Updated By',   finding.updated_by || '—'],
                  ['Table',        finding.table_source],
                ].map(([k, v]) => (
                  <Box key={k} sx={{ display: 'flex', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 110 }}>{k}:</Typography>
                    <Typography variant="body2" fontWeight="medium">{v}</Typography>
                  </Box>
                ))}
                {finding.extra && Object.entries(finding.extra).filter(([, v]) => v).map(([k, v]) => (
                  <Box key={k} sx={{ display: 'flex', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 110, textTransform: 'capitalize' }}>
                      {k.replace(/_/g, ' ')}:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">{String(v)}</Typography>
                  </Box>
                ))}
              </Box>
            </Grid>

            {/* Basic Flags */}
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>DETECTED FLAGS</Typography>
              {finding.basic_flags?.length > 0
                ? <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.8 }}>
                    {finding.basic_flags.map((f, i) => <FlagBadge key={i} flag={f} />)}
                  </Box>
                : <Typography variant="body2" color="text.secondary">No basic flags detected</Typography>
              }
            </Grid>

            {/* AI Summary */}
            {finding.ai_summary && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>AI SUMMARY</Typography>
                <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8fafc', borderRadius: 2, border: '1px solid #e2e8f0' }}>
                  <Typography variant="body2">{finding.ai_summary}</Typography>
                </Paper>
              </Grid>
            )}

            {/* AI Issues */}
            {finding.ai_issues?.length > 0 && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1.5 }}>ISSUES FOUND</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {finding.ai_issues.map((issue, i) => (
                    <Paper key={i} elevation={0} sx={{ p: 2, borderRadius: 2, border: `1px solid ${riskCfg.border}`, bgcolor: riskCfg.bg }}>
                      <Typography variant="body2" fontWeight="bold" color={riskCfg.text} sx={{ mb: 0.5 }}>
                        {issue.type}
                      </Typography>
                      <Typography variant="body2" sx={{ mb: 0.5 }}>{issue.detail}</Typography>
                      {issue.line_hint && issue.line_hint !== 'N/A' && (
                        <Typography variant="caption" sx={{ fontFamily: 'monospace', bgcolor: '#1e293b', color: '#a6e22e', px: 1, py: 0.3, borderRadius: 1, display: 'inline-block' }}>
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
                <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>RECOMMENDATION</Typography>
                <Paper elevation={0} sx={{ p: 2, bgcolor: '#f0fdf4', border: '1px solid #86efac', borderRadius: 2 }}>
                  <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                    <RecommendIcon sx={{ color: '#16a34a', mt: 0.2, flexShrink: 0 }} />
                    <Typography variant="body2">{finding.recommendation}</Typography>
                  </Box>
                </Paper>
              </Grid>
            )}

            {/* Deactivate blocked notice */}
            {DEACTIVATE_BLOCKED_TABLES.has(finding.table_source) && (
              <Grid item xs={12}>
                <Alert severity="info" icon={<InfoOutlinedIcon />}>
                  Deactivation is disabled for <strong>{finding.table_source}</strong> — this is a protected system table. Review and act manually from ServiceNow.
                </Alert>
              </Grid>
            )}
          </Grid>
        </DialogContent>

        <DialogActions sx={{ p: 2.5, borderTop: '1px solid #e2e8f0', gap: 1 }}>
          <Button onClick={onClose} variant="outlined" sx={{ mr: 'auto' }}>Close</Button>

          <Button
            variant="outlined"
            startIcon={<OpenInNewIcon />}
            onClick={() => window.open(`https://abhrademo5.service-now.com/nav_to.do?uri=${finding.table_source}.do?sys_id=${finding.sys_id}`, '_blank')}
          >
            Open in ServiceNow
          </Button>

          {/* DEACTIVATE BUTTON — only shown when safe + record is active */}
          {canDeactivate && (
            <Button
              variant="contained"
              color="warning"
              startIcon={deactivating ? <CircularProgress size={16} color="inherit" /> : <HighlightOffIcon />}
              onClick={() => setConfirmOpen(true)}
              disabled={deactivating}
              sx={{ bgcolor: '#d97706', '&:hover': { bgcolor: '#b45309' } }}
            >
              {deactivating ? 'Deactivating...' : 'Deactivate Record'}
            </Button>
          )}

          {/* Already deactivated label */}
          {!isActive && !DEACTIVATE_BLOCKED_TABLES.has(finding.table_source) && (
            <Chip
              icon={<CheckCircleOutlineIcon />}
              label="Already Inactive"
              color="default"
              variant="outlined"
              size="small"
            />
          )}
        </DialogActions>
      </Dialog>

      {/* ── CONFIRMATION DIALOG ── */}
      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} maxWidth="xs" fullWidth
        PaperProps={{ sx: { borderRadius: 3, border: '2px solid #fcd34d' } }}>
        <DialogTitle sx={{ bgcolor: '#fffbeb', borderBottom: '1px solid #fcd34d' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <WarningAmberIcon sx={{ color: '#d97706' }} />
            <Typography fontWeight="bold">Confirm Deactivation</Typography>
          </Box>
        </DialogTitle>
        <DialogContent sx={{ pt: 3 }}>
          <Typography variant="body2" sx={{ mb: 2 }}>
            You are about to deactivate:
          </Typography>
          <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8fafc', borderRadius: 2, border: '1px solid #e2e8f0', mb: 2 }}>
            <Typography variant="body2" fontWeight="bold">{finding.name}</Typography>
            <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#64748b' }}>
              {finding.table_source}
            </Typography>
          </Paper>
          <Alert severity="warning" sx={{ mb: 1 }}>
            This will set <strong>active = false</strong> on the record. The script will stop executing immediately.
          </Alert>
          <Alert severity="info">
            This is fully reversible — open the record in ServiceNow and set active = true to re-enable it.
          </Alert>
        </DialogContent>
        <DialogActions sx={{ p: 2, gap: 1 }}>
          <Button onClick={() => setConfirmOpen(false)} variant="outlined" fullWidth>
            Cancel
          </Button>
          <Button
            onClick={handleDeactivate}
            variant="contained"
            color="warning"
            fullWidth
            sx={{ bgcolor: '#d97706', '&:hover': { bgcolor: '#b45309' } }}
          >
            Yes, Deactivate
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

// =====================================================================
// TECH DEBT TOOL
// =====================================================================
function TechDebtTool() {
  const [availableTables, setAvailableTables]   = useState([]);
  const [selectedTables, setSelectedTables]     = useState([]);
  const [limit, setLimit]                       = useState(100);
  const [loading, setLoading]                   = useState(false);
  const [loadingTables, setLoadingTables]       = useState(true);
  const [result, setResult]                     = useState(null);
  const [error, setError]                       = useState(null);
  const [selectedFinding, setSelectedFinding]   = useState(null);
  const [dialogOpen, setDialogOpen]             = useState(false);
  const [riskFilter, setRiskFilter]             = useState('All');
  const [deactivatedIds, setDeactivatedIds]     = useState(new Set());

  // Called by dialog after successful deactivation — updates row live
  const handleDeactivated = (sys_id) => {
    setDeactivatedIds(prev => new Set([...prev, sys_id]));
    setResult(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        findings: prev.findings.map(f =>
          f.sys_id === sys_id ? { ...f, active: 'false' } : f
        )
      };
    });
    setSelectedFinding(prev =>
      prev && prev.sys_id === sys_id ? { ...prev, active: 'false' } : prev
    );
  };

  // Fetch available tables on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/debt-tables`)
      .then(r => r.json())
      .then(data => {
        setAvailableTables(data.tables || []);
        // Pre-select Phase 1 tables by default
        const phase1 = (data.tables || []).filter(t => t.phase === 1).map(t => t.table);
        setSelectedTables(phase1);
      })
      .catch(() => setError('Could not load table list from backend.'))
      .finally(() => setLoadingTables(false));
  }, []);

  const toggleTable = (table) => {
    setSelectedTables(prev =>
      prev.includes(table) ? prev.filter(t => t !== table) : [...prev, table]
    );
  };

  const handleScan = async () => {
    if (selectedTables.length === 0) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE}/api/scan-debt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tables: selectedTables, limit }),
      });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Scan failed');
      }
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const openFinding = (finding) => {
    setSelectedFinding(finding);
    setDialogOpen(true);
  };

  // Filter findings by selected risk
  const filteredFindings = result?.findings?.filter(f =>
    riskFilter === 'All' ? true : f.risk_level === riskFilter
  ) || [];

  // Group tables by phase
  const phase1Tables = availableTables.filter(t => t.phase === 1);
  const phase2Tables = availableTables.filter(t => t.phase === 2);

  return (
    <Box sx={{ animation: 'fadeIn 0.5s ease-in' }}>

      {/* ── SCAN SETUP CARD ── */}
      <Card elevation={0} sx={{ mb: 3, border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" fontWeight="bold" color="primary" sx={{ mb: 0.5 }}>
            Technical Debt Clearance
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Select the ServiceNow tables to scan. The tool reads configurations, applies rule checks, and uses AI to identify debt — nothing is modified.
          </Typography>

          {loadingTables ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={18} />
              <Typography variant="body2" color="text.secondary">Loading available tables...</Typography>
            </Box>
          ) : (
            <Grid container spacing={3}>
              {/* Phase 1 */}
              <Grid item xs={12} md={6}>
                {/* <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>
                  PHASE 1 — Scripts & Rules
                </Typography> */}
                <FormGroup>
                  {phase1Tables.map(t => (
                    <FormControlLabel
                      key={t.table}
                      control={
                        <Checkbox
                          checked={selectedTables.includes(t.table)}
                          onChange={() => toggleTable(t.table)}
                          size="small"
                          disabled={loading}
                        />
                      }
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2">{t.label}</Typography>
                          <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#94a3b8' }}>({t.table})</Typography>
                        </Box>
                      }
                    />
                  ))}
                </FormGroup>
              </Grid>

              {/* Phase 2 */}
              <Grid item xs={12} md={6}>
                {/* <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>
                  PHASE 2 — Flows, Catalog & Policies
                </Typography> */}
                <FormGroup>
                  {phase2Tables.map(t => (
                    <FormControlLabel
                      key={t.table}
                      control={
                        <Checkbox
                          checked={selectedTables.includes(t.table)}
                          onChange={() => toggleTable(t.table)}
                          size="small"
                          disabled={loading}
                        />
                      }
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2">{t.label}</Typography>
                          <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#94a3b8' }}>({t.table})</Typography>
                        </Box>
                      }
                    />
                  ))}
                </FormGroup>
              </Grid>

              {/* Limit + Scan Button */}
              <Grid item xs={12}>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
                      Records per table:
                    </Typography>
                    <TextField
                      type="number"
                      size="small"
                      value={limit}
                      onChange={e => setLimit(Number(e.target.value))}
                      disabled={loading}
                      inputProps={{ min: 10, max: 500, step: 10 }}
                      sx={{ width: 100 }}
                    />
                    <Tooltip title="Max records fetched from each selected table via ServiceNow Table API (sysparm_limit). Higher = slower scan but more coverage.">
                      <InfoOutlinedIcon sx={{ color: '#94a3b8', fontSize: 18, cursor: 'help' }} />
                    </Tooltip>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 'auto' }}>
                    <Chip
                      label={`${selectedTables.length} table${selectedTables.length !== 1 ? 's' : ''} selected`}
                      size="small"
                      color={selectedTables.length > 0 ? 'primary' : 'default'}
                      variant="outlined"
                    />
                    <Button
                      variant="contained"
                      size="large"
                      onClick={handleScan}
                      disabled={loading || selectedTables.length === 0}
                      startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <PlayArrowIcon />}
                      sx={{ px: 4 }}
                    >
                      {loading ? 'Scanning...' : 'Start Scan'}
                    </Button>
                  </Box>
                </Box>
              </Grid>
            </Grid>
          )}

          {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        </CardContent>
      </Card>

      {/* ── LOADING STATE ── */}
      {loading && (
        <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2, p: 4, textAlign: 'center' }}>
          <CircularProgress size={50} sx={{ mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>Scanning ServiceNow...</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Reading records → Applying rule checks → Running AI analysis
          </Typography>
          <LinearProgress sx={{ maxWidth: 400, mx: 'auto', borderRadius: 4 }} />
        </Card>
      )}

      {/* ── RESULTS ── */}
      {result && !loading && (
        <Box>
          {/* Summary Stats */}
          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <StatCard label="Total Scanned"  value={result.summary.total_scanned} color="#3b82f6" icon={<StorageIcon />} />
            <StatCard label="High Risk"      value={result.summary.high_risk}     color="#dc2626" icon={<ErrorOutlineIcon />} />
            <StatCard label="Medium Risk"    value={result.summary.medium_risk}   color="#d97706" icon={<WarningAmberIcon />} />
            <StatCard label="Low Risk"       value={result.summary.low_risk}      color="#16a34a" icon={<InfoOutlinedIcon />} />
            <StatCard label="Inactive"       value={result.summary.inactive}      color="#7c3aed" icon={<BugReportIcon />} />
            <StatCard label="Stale (2yr+)"   value={result.summary.stale}         color="#0891b2" icon={<FlagIcon />} />
          </Box>

          {/* By Table Breakdown */}
          {Object.keys(result.summary.by_table || {}).length > 0 && (
            <Card elevation={0} sx={{ mb: 3, border: '1px solid #e0e0e0', borderRadius: 2 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 2 }}>
                  SCANNED BY TABLE
                </Typography>
                <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
                  {Object.entries(result.summary.by_table).map(([table, count]) => (
                    <Chip
                      key={table}
                      label={`${table}: ${count}`}
                      size="small"
                      variant="outlined"
                      sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}

          {/* Risk Filter Tabs */}
          <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <FilterListIcon sx={{ color: '#94a3b8', mr: 0.5 }} />
            {['All', 'High', 'Medium', 'Low', 'None'].map(r => {
              const counts = {
                All:    result.findings.length,
                High:   result.summary.high_risk,
                Medium: result.summary.medium_risk,
                Low:    result.summary.low_risk,
                None:   result.summary.no_risk,
              };
              return (
                <Button
                  key={r}
                  size="small"
                  variant={riskFilter === r ? 'contained' : 'outlined'}
                  color={r === 'High' ? 'error' : r === 'Medium' ? 'warning' : r === 'Low' ? 'success' : 'primary'}
                  onClick={() => setRiskFilter(r)}
                  sx={{ minWidth: 0, px: 2 }}
                >
                  {r} {counts[r] !== undefined ? `(${counts[r]})` : ''}
                </Button>
              );
            })}
          </Box>

          {/* Findings Table */}
          <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: '#f8fafc' }}>
                    {['Component Name', 'Type', 'Active', 'Last Updated', 'Flags', 'Risk', 'AI Summary', ''].map(h => (
                      <TableCell key={h} sx={{ fontWeight: 'bold', fontSize: '0.75rem', color: '#64748b', py: 1.5 }}>
                        {h}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredFindings.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} align="center" sx={{ py: 5, color: '#94a3b8' }}>
                        No findings match this filter.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredFindings.map((finding, i) => {
                      const riskCfg = RISK_COLOR[finding.risk_level] || RISK_COLOR.None;
                      const wasDeactivated = deactivatedIds.has(finding.sys_id);
                      return (
                        <TableRow
                          key={i}
                          hover
                          sx={{
                            cursor: 'pointer',
                            bgcolor: wasDeactivated ? '#f0fdf4' : i % 2 === 0 ? 'white' : '#fafafa',
                            '&:hover': { bgcolor: `${riskCfg.bg} !important` },
                            borderLeft: `3px solid ${wasDeactivated ? '#16a34a' : riskCfg.border}`,
                            opacity: wasDeactivated ? 0.75 : 1,
                          }}
                          onClick={() => openFinding(finding)}
                        >
                          {/* Name */}
                          <TableCell sx={{ maxWidth: 200 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8 }}>
                              <Tooltip title={finding.name}>
                                <Typography variant="body2" fontWeight="medium" noWrap sx={{ maxWidth: 160 }}>
                                  {finding.name}
                                </Typography>
                              </Tooltip>
                              {wasDeactivated && (
                                <Chip label="Deactivated" size="small" color="success" sx={{ height: 18, fontSize: '0.65rem' }} />
                              )}
                            </Box>
                            <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#94a3b8' }}>
                              {finding.table_source}
                            </Typography>
                          </TableCell>

                          {/* Type */}
                          <TableCell>
                            <Chip label={finding.label} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                          </TableCell>

                          {/* Active */}
                          <TableCell>
                            {(finding.active === 'true' || finding.active === true) && !wasDeactivated
                              ? <CheckCircleOutlineIcon sx={{ color: '#16a34a', fontSize: 18 }} />
                              : <HighlightOffIcon sx={{ color: '#94a3b8', fontSize: 18 }} />
                            }
                          </TableCell>

                          {/* Last Updated */}
                          <TableCell>
                            <Typography variant="caption" color="text.secondary">
                              {finding.last_updated ? finding.last_updated.substring(0, 10) : '—'}
                            </Typography>
                          </TableCell>

                          {/* Flags */}
                          <TableCell sx={{ maxWidth: 200 }}>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.4 }}>
                              {finding.basic_flags?.slice(0, 2).map((f, fi) => (
                                <FlagBadge key={fi} flag={f} />
                              ))}
                              {finding.basic_flags?.length > 2 && (
                                <Chip label={`+${finding.basic_flags.length - 2}`} size="small" sx={{ height: 22, fontSize: '0.7rem' }} />
                              )}
                            </Box>
                          </TableCell>

                          {/* Risk */}
                          <TableCell>
                            <RiskChip level={finding.risk_level} />
                          </TableCell>

                          {/* AI Summary */}
                          <TableCell sx={{ maxWidth: 220 }}>
                            <Tooltip title={finding.ai_summary}>
                              <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 210, display: 'block' }}>
                                {finding.ai_summary || '—'}
                              </Typography>
                            </Tooltip>
                          </TableCell>

                          {/* Action */}
                          <TableCell>
                            <Button size="small" variant="text" endIcon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
                              onClick={e => { e.stopPropagation(); openFinding(finding); }}>
                              Details
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>

          {/* Export raw JSON */}
          <Accordion elevation={0} sx={{ mt: 2, border: '1px solid #e0e0e0', borderRadius: '8px !important', '&:before': { display: 'none' } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight="bold" color="text.secondary">View Raw Scan Output (JSON)</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Paper sx={{ p: 2, backgroundColor: '#1e1e1e', color: '#a6e22e', overflowX: 'auto', maxHeight: '400px' }}>
                <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '12px', textAlign: 'left' }}>
                  {JSON.stringify(result, null, 2)}
                </pre>
              </Paper>
            </AccordionDetails>
          </Accordion>
        </Box>
      )}

      {/* Finding Detail Dialog */}
      <FindingDetailDialog
        finding={selectedFinding}
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onDeactivated={handleDeactivated}
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

// =====================================================================
// TOOL 1: NEW MODULE DEVELOPMENT
// =====================================================================
// function NewModuleTool() {
//   const [prompt, setPrompt] = useState('');
//   const [loading, setLoading] = useState(false);
//   const [result, setResult] = useState(null);
//   const [error, setError] = useState(null);
//   const [blueprint,     setBlueprint]     = useState(null);
//   const [buildLoading,  setBuildLoading]  = useState(false);

//   // const handleGenerate = async () => {
//   //   if (!prompt) return;
//   //   setLoading(true);
//   //   setError(null);
//   //   setResult(null);

//   //   try {
//   //     const response = await fetch(`${API_BASE}/api/build-app`, {
//   //       method: 'POST',
//   //       headers: { 'Content-Type': 'application/json' },
//   //       body: JSON.stringify({ prompt }),
//   //     });
//   //     if (!response.ok) throw new Error('Failed to generate application');
//   //     const data = await response.json();
//   //     setResult(data.data.raw_blueprint);
//   //   } catch (err) {
//   //     setError(err.message);
//   //   } finally {
//   //     setLoading(false);
//   //   }
//   // };

//   // Phase 1: AI generates blueprint only (no SN writes)
//   // In NewModuleTool
//   const handleGenerate = async () => {
//     if (!prompt) return;
//     setLoading(true);
//     setError(null);
//     setResult(null);
//     setBlueprint(null);

//     try {
//       console.log('→ Calling /api/generate-blueprint with:', prompt);

//       const response = await fetch(`${API_BASE}/api/generate-blueprint`, {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ prompt }),
//       });

//       console.log('→ Response status:', response.status, response.ok);

//       const data = await response.json();
//       console.log('→ Response body:', data);

//       if (!response.ok) {
//         throw new Error(data.detail || data.error || 'Failed to generate blueprint');
//       }
//       if (!data.blueprint) {
//         throw new Error('Backend returned no blueprint. Check FastAPI logs.');
//       }

//       setBlueprint(data.blueprint);
//     } catch (err) {
//       console.error('→ handleGenerate error:', err);
//       setError(err.message);
//     } finally {
//       setLoading(false);
//     }
//   };

//   // Phase 2: User clicked "Add into ServiceNow" after validation passed
//   const handleBuild = async () => {
//     if (!blueprint) return;
//     setBuildLoading(true);
//     setError(null);
//     try {
//       const response = await fetch(`${API_BASE}/api/build-from-blueprint`, {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ blueprint }),
//       });
//       if (!response.ok) throw new Error('Build failed');
//       const data = await response.json();
//       setResult(data.data.raw_blueprint);
//     } catch (err) {
//       setError(err.message);
//     } finally {
//       setBuildLoading(false);
//     }
//   };

//   return (
//     <Box sx={{ animation: 'fadeIn 0.5s ease-in' }}>
//       <Card elevation={0} sx={{ mb: 4, border: '1px solid #e0e0e0', borderRadius: 2 }}>
//         <CardContent sx={{ p: 4 }}>
//           <Typography variant="h5" fontWeight="bold" color="primary" sx={{ mb: 1 }}>New Module Development</Typography>
//           <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
//             Type a requirement below to instantly generate and deploy a ServiceNow module.
//           </Typography>
//           <Box sx={{ display: 'flex', gap: 2 }}>
//             <TextField fullWidth variant="outlined" placeholder="e.g., Create a Vendor Management System..."
//               value={prompt} onChange={(e) => setPrompt(e.target.value)} disabled={loading} />
//             <Button variant="contained" size="large" onClick={handleGenerate} disabled={loading || !prompt}
//               startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <AutoAwesomeIcon />}
//               sx={{ px: 4, whiteSpace: 'nowrap' }}>
//               {loading ? 'Building...' : 'Generate Module'}
//             </Button>
//           </Box>
//           {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
//         </CardContent>
//       </Card>

//       {loading && (
//         <Box sx={{ textAlign: 'center', py: 10 }}>
//           <CircularProgress size={50} sx={{ mb: 2 }} />
//           <Typography variant="h6" color="text.secondary">Architecting the solution...</Typography>
//         </Box>
//       )}

//       {blueprint && !result && !loading && (
//             <Box sx={{ mt: 3 }}>
//               {/* Blueprint preview */}
//               <Card elevation={0} sx={{ mb: 3, border: '1px solid #e2e8f0', borderRadius: 2 }}>
//                 <CardContent sx={{ p: 3 }}>
//                   <Box sx={{ pl: 1, borderLeft: '4px solid #1976d2', mb: 2 }}>
//                     <Typography variant="h6" fontWeight="bold">
//                       {blueprint.module_name}
//                     </Typography>
//                     <Typography variant="body2" color="text.secondary">
//                       {blueprint.description}
//                     </Typography>
//                   </Box>
//                   <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
//                     {[
//                       { label: 'Tables',    value: blueprint.tables?.length        || 0, color: '#3b82f6' },
//                       { label: 'Roles',     value: blueprint.roles?.length         || 0, color: '#f59e0b' },
//                       { label: 'Workflows', value: blueprint.workflows?.length     || 0, color: '#10b981' },
//                       { label: 'Forms',     value: blueprint.forms?.length         || 0, color: '#8b5cf6' },
//                     ].map(s => (
//                       <Chip key={s.label}
//                         label={`${s.value} ${s.label}`}
//                         size="small" variant="outlined"
//                         sx={{ borderColor: s.color, color: s.color, fontWeight: 'bold' }} />
//                     ))}
//                   </Box>
//                 </CardContent>
//               </Card>

//               {/* Validator */}
//               {/* Validator + Push button — collapsible */}
//               <ValidatorToggle
//                 blueprint={blueprint}
//                 validateEndpoint={
//                   routing?.intent === 'scoped_app'
//                     ? '/api/validate-scoped-app'
//                     : '/api/validate-module'
//                 }
//                 onConfirmed={handleBuild}
//                 buildLoading={buildLoading}
//               />
//             </Box>
//           )}

//       {result && !loading && (
//         <Box>
//           <Box sx={{ mb: 4, pl: 1, borderLeft: '4px solid #1976d2' }}>
//             <Typography variant="h5" fontWeight="bold">{result.module_name}</Typography>
//             <Typography variant="body1" color="text.secondary">{result.description}</Typography>
//           </Box>
//           <Grid container spacing={3} sx={{ mb: 4 }}>
//             <Grid item xs={12} md={6}>
//               <Card elevation={0} sx={{ height: '100%', border: '1px solid #e0e0e0', borderRadius: 2 }}>
//                 <CardContent>
//                   <Typography variant="h6" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
//                     <TableChartIcon color="success" /> Database Tables
//                     <Chip label="Pushed to ServiceNow" color="success" size="small" sx={{ ml: 'auto' }} />
//                   </Typography>
//                   <Divider sx={{ mb: 2 }} />
//                   {result.tables?.map((table, idx) => (
//                     <Box key={idx} sx={{ mb: 3 }}>
//                       <Typography fontWeight="bold" color="primary">{table.table_label}</Typography>
//                       <Typography variant="caption" sx={{ fontFamily: 'monospace', bgcolor: '#f5f5f5', px: 1, borderRadius: 1 }}>{table.table_name}</Typography>
//                       <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
//                         {table.fields?.map((field, fIdx) => (
//                           <Chip key={fIdx} label={`${field.field_label} (${field.internal_type})`} size="small" variant="outlined" />
//                         ))}
//                       </Box>
//                     </Box>
//                   ))}
//                 </CardContent>
//               </Card>
//             </Grid>
//             <Grid item xs={12} md={6}>
//               <Card elevation={0} sx={{ height: '100%', border: '1px solid #e0e0e0', borderRadius: 2 }}>
//                 <CardContent>
//                   <Typography variant="h6" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
//                     <SecurityIcon color="warning" /> Security Roles
//                     <Chip label="Pushed to ServiceNow" color="success" size="small" sx={{ ml: 'auto' }} />
//                   </Typography>
//                   <Divider sx={{ mb: 2 }} />
//                   <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
//                     {result.roles?.map((role, idx) => (
//                       <Chip key={idx} label={role} color="default" sx={{ fontFamily: 'monospace' }} />
//                     ))}
//                   </Box>
//                 </CardContent>
//               </Card>
//             </Grid>
//             <Grid item xs={12} md={6}>
//               <Card elevation={0} sx={{ height: '100%', border: '1px solid #e0e0e0', borderRadius: 2 }}>
//                 <CardContent>
//                   <Typography variant="h6" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
//                     <AccountTreeIcon color="info" /> Automations & Workflows
//                     <Chip label="Pushed to ServiceNow" color="success" size="small" sx={{ ml: 'auto' }} />
//                   </Typography>
//                   <Divider sx={{ mb: 2 }} />
//                   {result.workflows?.map((wf, idx) => (
//                     <Box key={idx} sx={{ mb: 2, p: 2, bgcolor: '#f8fafc', borderRadius: 2 }}>
//                       <Typography fontWeight="bold">{wf.name}</Typography>
//                       <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Trigger: {wf.trigger}</Typography>
//                       <ol style={{ margin: 0, paddingLeft: '20px', fontSize: '0.875rem', color: '#475569' }}>
//                         {wf.steps?.map((step, sIdx) => <li key={sIdx}>{step}</li>)}
//                       </ol>
//                     </Box>
//                   ))}
//                 </CardContent>
//               </Card>
//             </Grid>
//             <Grid item xs={12} md={6}>
//               <Card elevation={0} sx={{ height: '100%', border: '1px solid #e0e0e0', borderRadius: 2 }}>
//                 <CardContent>
//                   <Typography variant="h6" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
//                     <FactCheckIcon color="secondary" /> Approvals & Alerts
//                     <Chip label="Pushed to ServiceNow" color="success" size="small" sx={{ ml: 'auto' }} />
//                   </Typography>
//                   <Divider sx={{ mb: 2 }} />
//                   {result.approvals?.map((appr, idx) => (
//                     <Box key={`appr-${idx}`} sx={{ mb: 2 }}>
//                       <Typography fontWeight="bold">Approval: {appr.name}</Typography>
//                       <Typography variant="body2">Condition: {appr.condition}</Typography>
//                       <Typography variant="body2">Approver: <span style={{ fontFamily: 'monospace' }}>{appr.approver_role}</span></Typography>
//                     </Box>
//                   ))}
//                   <Divider sx={{ my: 2 }} />
//                   {result.notifications?.map((notif, idx) => (
//                     <Box key={`notif-${idx}`} sx={{ mb: 1 }}>
//                       <Typography fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><EmailIcon fontSize="small" /> {notif.name}</Typography>
//                       <Typography variant="body2" color="text.secondary">Trigger: {notif.trigger}</Typography>
//                     </Box>
//                   ))}
//                 </CardContent>
//               </Card>
//             </Grid>
//           </Grid>
//           <Accordion elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: '8px !important', '&:before': { display: 'none' } }}>
//             <AccordionSummary expandIcon={<ExpandMoreIcon />}>
//               <Typography fontWeight="bold" color="text.secondary">View Raw AI JSON Output</Typography>
//             </AccordionSummary>
//             <AccordionDetails>
//               <Paper sx={{ p: 2, backgroundColor: '#1e1e1e', color: '#a6e22e', overflowX: 'auto', maxHeight: '400px' }}>
//                 <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '13px', textAlign: 'left' }}>
//                   {JSON.stringify(result, null, 2)}
//                 </pre>
//               </Paper>
//             </AccordionDetails>
//           </Accordion>
//         </Box>
//       )}
//     </Box>
//   );
// }

// =====================================================================
// UPDATED NewModuleTool — paste this OVER the existing NewModuleTool
// function in App.jsx. Everything else in App.jsx stays the same.
//
// Changes:
//   1. Imports DiscoveryPanel at top of App.jsx (add this line):
//      import DiscoveryPanel from './DiscoveryPanel';
//
//   2. Replace the entire NewModuleTool function with the one below.
// =====================================================================

function NewModuleTool() {
  const [prompt,        setPrompt]        = useState('');
  const [moduleName,    setModuleName]     = useState('');   // extracted from prompt for discovery
  const [phase,         setPhase]         = useState('input');
  // phases: input → discovering → feature_select → generating → validating → result

  const [selectedFeatures, setSelectedFeatures] = useState([]);
  const [blueprint,     setBlueprint]     = useState(null);
  const [buildLoading,  setBuildLoading]  = useState(false);
  const [result,        setResult]        = useState(null);
  const [error,         setError]         = useState(null);

  const loading = phase === 'generating';

  // ── Step 1: User clicks "Check & Build" ─────────────────────────────────
  // Extract module name from prompt and kick off discovery
  const handleCheckAndBuild = () => {
    if (!prompt.trim()) return;

    // Simple extraction: use the full prompt as module name seed.
    // Backend's discover_module will handle keyword matching.
    // We strip common filler words to get a cleaner name.
    const cleaned = prompt
      .replace(/create|build|generate|make|develop|scaffold|a new|the|module|system|app|application/gi, '')
      .trim()
      .replace(/\s+/g, ' ')
      .trim();

    setModuleName(cleaned || prompt.trim());
    setPhase('discovering');
    setError(null);
    setBlueprint(null);
    setResult(null);
    setSelectedFeatures([]);
  };

  // ── Step 2: User selected features from DiscoveryPanel ──────────────────
  const handleFeaturesSelected = async (features) => {
    setSelectedFeatures(features);
    setPhase('generating');
    setError(null);
    setBlueprint(null);

    try {
      const response = await fetch(`${API_BASE}/api/generate-blueprint`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          prompt:           prompt,
          selected_features: features,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || data.error || 'Failed to generate blueprint');
      if (!data.blueprint) throw new Error('Backend returned no blueprint.');

      setBlueprint(data.blueprint);
      setPhase('validating');
    } catch (err) {
      setError(err.message);
      setPhase('feature_select');
    }
  };

  // ── Step 3: User confirmed via validator → push to ServiceNow ───────────
  const handleBuild = async () => {
    if (!blueprint) return;
    setBuildLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/build-from-blueprint`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ blueprint }),
      });
      if (!response.ok) throw new Error('Build failed');
      const data = await response.json();
      setResult(data.data);
      setPhase('result');
    } catch (err) {
      setError(err.message);
    } finally {
      setBuildLoading(false);
    }
  };

  const handleReset = () => {
    setPhase('input');
    setPrompt('');
    setModuleName('');
    setBlueprint(null);
    setResult(null);
    setError(null);
    setSelectedFeatures([]);
  };

  return (
    <Box sx={{ animation: 'fadeIn 0.5s ease-in' }}>

      {/* ── STEP 1: Prompt input ── */}
      <Card elevation={0} sx={{ mb: 3, border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" fontWeight="bold" color="primary" sx={{ mb: 1 }}>
            New Module Development
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Describe the module you need. The tool will first check if it already exists
            in ServiceNow, then let you choose exactly which features to create.
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="e.g., Create a Vendor Management module with approval workflow..."
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              disabled={phase !== 'input'}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleCheckAndBuild(); }}}
            />
            {phase === 'input' ? (
              <Button
                variant="contained"
                size="large"
                onClick={handleCheckAndBuild}
                disabled={!prompt.trim()}
                startIcon={<SearchIcon />}
                sx={{ px: 3, whiteSpace: 'nowrap', bgcolor: '#6366f1', '&:hover': { bgcolor: '#4f46e5' } }}
              >
                Check & Build
              </Button>
            ) : (
              <Button
                variant="outlined"
                size="large"
                onClick={handleReset}
                sx={{ px: 3, whiteSpace: 'nowrap' }}
              >
                Start Over
              </Button>
            )}
          </Box>
          {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        </CardContent>
      </Card>

      {/* ── STEP 2: Discovery + Feature Selection ── */}
      {(phase === 'discovering' || phase === 'feature_select') && (
        <DiscoveryPanel
          moduleName={moduleName}
          onFeaturesSelected={handleFeaturesSelected}
          onCancel={handleReset}
        />
      )}

      {/* ── STEP 3: Generating blueprint ── */}
      {phase === 'generating' && (
        <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 2, p: 4, textAlign: 'center' }}>
          <CircularProgress size={48} sx={{ mb: 2, color: '#6366f1' }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            Generating Blueprint...
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Building blueprint for: {selectedFeatures.map(f =>
              f.replace(/_/g, ' ')
            ).join(', ')}
          </Typography>
          <LinearProgress sx={{ maxWidth: 400, mx: 'auto', borderRadius: 4,
            '& .MuiLinearProgress-bar': { bgcolor: '#6366f1' } }} />
        </Card>
      )}

      {/* ── STEP 4: Blueprint preview + Validation ── */}
      {phase === 'validating' && blueprint && (
        <Box>
          {/* Blueprint summary */}
          <Card elevation={0} sx={{ mb: 3, border: '1px solid #e2e8f0', borderRadius: 2 }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ pl: 1.5, borderLeft: '4px solid #6366f1', mb: 2 }}>
                <Typography variant="h6" fontWeight="bold">
                  {blueprint.module_name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {blueprint.description}
                </Typography>
              </Box>

              {/* Selected features summary */}
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
                {selectedFeatures.map(f => (
                  <Chip key={f}
                    label={f.replace(/_/g, ' ')}
                    size="small" variant="outlined"
                    sx={{ borderColor: '#6366f1', color: '#6366f1', fontSize: '0.72rem' }} />
                ))}
              </Box>

              {/* Component counts */}
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {[
                  { label: 'Tables',    value: blueprint.tables?.length    || 0, color: '#3b82f6' },
                  { label: 'Roles',     value: blueprint.roles?.length     || 0, color: '#f59e0b' },
                  { label: 'Workflows', value: blueprint.workflows?.length || 0, color: '#10b981' },
                  { label: 'Forms',     value: blueprint.forms?.length     || 0, color: '#8b5cf6' },
                ].filter(s => s.value > 0).map(s => (
                  <Chip key={s.label}
                    label={`${s.value} ${s.label}`}
                    size="small"
                    sx={{ bgcolor: `${s.color}15`, color: s.color,
                          border: `1px solid ${s.color}40`, fontWeight: 'bold' }} />
                ))}
              </Box>
            </CardContent>
          </Card>

          {/* Validator */}
          <ValidatorToggle
            blueprint={blueprint}
            validateEndpoint="/api/validate-module"
            onConfirmed={handleBuild}
            buildLoading={buildLoading}
            selectedFeatures={selectedFeatures} 
          />
        </Box>
      )}

      {/* ── STEP 5: Build result ── */}
      {phase === 'result' && result && (
        <Box>
          <Alert severity="success" sx={{ mb: 3 }}>
            ✅ Module successfully created in ServiceNow!
          </Alert>

          <Box sx={{ mb: 3, pl: 1.5, borderLeft: '4px solid #6366f1' }}>
            <Typography variant="h5" fontWeight="bold">{result.module_name}</Typography>
            <Typography variant="body1" color="text.secondary">{result.description}</Typography>
          </Box>

          <Grid container spacing={2} sx={{ mb: 3 }}>
            {[
              { label: 'Tables Created',        value: result.tables_created?.length,        color: '#3b82f6' },
              { label: 'Fields Created',         value: result.fields_created?.length,        color: '#6366f1' },
              { label: 'Roles Created',          value: result.roles_created?.length,         color: '#f59e0b' },
              { label: 'Forms Created',          value: result.forms_created?.length,         color: '#8b5cf6' },
              { label: 'Workflows Created',      value: result.workflows_created?.length,     color: '#10b981' },
              { label: 'Notifications Created',  value: result.notifications_created?.length, color: '#0ea5e9' },
              { label: 'Approvals Created',      value: result.approvals_created?.length,     color: '#f97316' },
              { label: 'Navigation Created',     value: result.navigation_created?.length,    color: '#64748b' },
            ].filter(s => s.value > 0).map(s => (
              <Grid item xs={6} sm={4} md={3} key={s.label}>
                <Paper elevation={0} sx={{
                  p: 2, textAlign: 'center',
                  border: `1px solid ${s.color}30`,
                  borderTop: `3px solid ${s.color}`,
                  borderRadius: 2,
                }}>
                  <Typography variant="h4" fontWeight="bold" sx={{ color: s.color, lineHeight: 1 }}>
                    {s.value}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">{s.label}</Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Button variant="outlined" onClick={handleReset}
            sx={{ borderColor: '#6366f1', color: '#6366f1' }}>
            Build Another Module
          </Button>
        </Box>
      )}
    </Box>
  );
}

// =====================================================================
// TOOL 2: SCOPED APP DEVELOPMENT
// =====================================================================
function ScopedAppTool() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [blueprint,     setBlueprint]     = useState(null);
  const [buildLoading,  setBuildLoading]  = useState(false);

  // In NewModuleTool
  const handleGenerate = async () => {
    if (!prompt) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setBlueprint(null);

    try {
      console.log('→ Calling /api/generate-scoped-blueprint with:', prompt);

      const response = await fetch(`${API_BASE}/api/generate-scoped-blueprint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      console.log('→ Response status:', response.status, response.ok);

      const data = await response.json();
      console.log('→ Response body:', data);

      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Failed to generate blueprint');
      }
      if (!data.blueprint) {
        throw new Error('Backend returned no blueprint. Check FastAPI logs.');
      }

      setBlueprint(data.blueprint);
    } catch (err) {
      console.error('→ handleGenerate error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Phase 2: User clicked "Add into ServiceNow" after validation passed
  const handleBuild = async () => {
    if (!blueprint) return;
    setBuildLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/build-scoped-from-blueprint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blueprint }),
      });
      if (!response.ok) throw new Error('Build failed');
      const data = await response.json();
      setResult(data.data.raw_blueprint);
    } catch (err) {
      setError(err.message);
    } finally {
      setBuildLoading(false);
    }
  };

  return (
    <Box sx={{ animation: 'fadeIn 0.5s ease-in' }}>
      <Card elevation={0} sx={{ mb: 4, border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" fontWeight="bold" color="primary" sx={{ mb: 1 }}>Scoped App Development</Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Type a requirement below to instantly generate and deploy a ServiceNow module.
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField fullWidth variant="outlined" placeholder="e.g., Create a Vendor Management System..."
              value={prompt} onChange={(e) => setPrompt(e.target.value)} disabled={loading} />
            <Button variant="contained" size="large" onClick={handleGenerate} disabled={loading || !prompt}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <AutoAwesomeIcon />}
              sx={{ px: 4, whiteSpace: 'nowrap' }}>
              {loading ? 'Building...' : 'Generate Module'}
            </Button>
          </Box>
          {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        </CardContent>
      </Card>

      {loading && (
        <Box sx={{ textAlign: 'center', py: 10 }}>
          <CircularProgress size={50} sx={{ mb: 2 }} />
          <Typography variant="h6" color="text.secondary">Architecting the solution...</Typography>
        </Box>
      )}

      {blueprint && !result && !loading && (
            <Box sx={{ mt: 3 }}>
              {/* Blueprint preview */}
              <Card elevation={0} sx={{ mb: 3, border: '1px solid #e2e8f0', borderRadius: 2 }}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ pl: 1, borderLeft: '4px solid #1976d2', mb: 2 }}>
                    <Typography variant="h6" fontWeight="bold">
                      {blueprint.module_name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {blueprint.description}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
                    {[
                      { label: 'Tables',    value: blueprint.tables?.length        || 0, color: '#3b82f6' },
                      { label: 'Roles',     value: blueprint.roles?.length         || 0, color: '#f59e0b' },
                      { label: 'Workflows', value: blueprint.workflows?.length     || 0, color: '#10b981' },
                      { label: 'Forms',     value: blueprint.forms?.length         || 0, color: '#8b5cf6' },
                    ].map(s => (
                      <Chip key={s.label}
                        label={`${s.value} ${s.label}`}
                        size="small" variant="outlined"
                        sx={{ borderColor: s.color, color: s.color, fontWeight: 'bold' }} />
                    ))}
                  </Box>
                </CardContent>
              </Card>

              {/* Validator */}
              {/* Validator + Push button — collapsible */}
              <ValidatorToggle
                blueprint={blueprint}
                validateEndpoint={
                  routing?.intent === 'scoped_app'
                    ? '/api/validate-scoped-app'
                    : '/api/validate-module'
                }
                onConfirmed={handleBuild}
                buildLoading={buildLoading}
                selectedFeatures={selectedFeatures} 
              />
            </Box>
          )}

      {result && !loading && (
        <Box>
          <Box sx={{ mb: 4, pl: 1, borderLeft: '4px solid #1976d2' }}>
            <Typography variant="h5" fontWeight="bold">{result.app_name}</Typography>
            <Typography variant="body1" color="text.secondary">{result.description}</Typography>
          </Box>
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} md={6}>
              <Card elevation={0} sx={{ height: '100%', border: '1px solid #e0e0e0', borderRadius: 2 }}>
                <CardContent>
                  <Typography variant="h6" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <TableChartIcon color="success" /> Database Tables
                    <Chip label="Pushed to ServiceNow" color="success" size="small" sx={{ ml: 'auto' }} />
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  {result.tables?.map((table, idx) => (
                    <Box key={idx} sx={{ mb: 3 }}>
                      <Typography fontWeight="bold" color="primary">{table.table_label}</Typography>
                      <Typography variant="caption" sx={{ fontFamily: 'monospace', bgcolor: '#f5f5f5', px: 1, borderRadius: 1 }}>{table.table_name}</Typography>
                      <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {table.fields?.map((field, fIdx) => (
                          <Chip key={fIdx} label={`${field.field_label} (${field.internal_type})`} size="small" variant="outlined" />
                        ))}
                      </Box>
                    </Box>
                  ))}
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card elevation={0} sx={{ height: '100%', border: '1px solid #e0e0e0', borderRadius: 2 }}>
                <CardContent>
                  <Typography variant="h6" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <SecurityIcon color="warning" /> Security Roles
                    <Chip label="Pushed to ServiceNow" color="success" size="small" sx={{ ml: 'auto' }} />
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {result.roles?.map((role, idx) => (
                      <Chip key={idx} label={role} color="default" sx={{ fontFamily: 'monospace' }} />
                    ))}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card elevation={0} sx={{ height: '100%', border: '1px solid #e0e0e0', borderRadius: 2 }}>
                <CardContent>
                  <Typography variant="h6" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <AccountTreeIcon color="info" /> Automations & Workflows
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  {result.workflows?.map((wf, idx) => (
                    <Box key={idx} sx={{ mb: 2, p: 2, bgcolor: '#f8fafc', borderRadius: 2 }}>
                      <Typography fontWeight="bold">{wf.name}</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Trigger: {wf.trigger}</Typography>
                      <ol style={{ margin: 0, paddingLeft: '20px', fontSize: '0.875rem', color: '#475569' }}>
                        {wf.steps?.map((step, sIdx) => <li key={sIdx}>{step}</li>)}
                      </ol>
                    </Box>
                  ))}
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card elevation={0} sx={{ height: '100%', border: '1px solid #e0e0e0', borderRadius: 2 }}>
                <CardContent>
                  <Typography variant="h6" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <FactCheckIcon color="secondary" /> Approvals & Alerts
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  {result.approvals?.map((appr, idx) => (
                    <Box key={`appr-${idx}`} sx={{ mb: 2 }}>
                      <Typography fontWeight="bold">Approval: {appr.name}</Typography>
                      <Typography variant="body2">Condition: {appr.condition}</Typography>
                      <Typography variant="body2">Approver: <span style={{ fontFamily: 'monospace' }}>{appr.approver_role}</span></Typography>
                    </Box>
                  ))}
                  <Divider sx={{ my: 2 }} />
                  {result.notifications?.map((notif, idx) => (
                    <Box key={`notif-${idx}`} sx={{ mb: 1 }}>
                      <Typography fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><EmailIcon fontSize="small" /> {notif.name}</Typography>
                      <Typography variant="body2" color="text.secondary">Trigger: {notif.trigger}</Typography>
                    </Box>
                  ))}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          <Accordion elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: '8px !important', '&:before': { display: 'none' } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight="bold" color="text.secondary">View Raw AI JSON Output</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Paper sx={{ p: 2, backgroundColor: '#1e1e1e', color: '#a6e22e', overflowX: 'auto', maxHeight: '400px' }}>
                <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '13px', textAlign: 'left' }}>
                  {JSON.stringify(result, null, 2)}
                </pre>
              </Paper>
            </AccordionDetails>
          </Accordion>
        </Box>
      )}
    </Box>
  );
}

// =====================================================================
// PLACEHOLDER
// =====================================================================
function PlaceholderTool({ title, description }) {
  return (
    <Box sx={{ textAlign: 'center', py: 10 }}>
      <Typography variant="h4" color="text.secondary" gutterBottom>{title}</Typography>
      <Typography variant="body1" color="text.secondary">{description}</Typography>
      <Box sx={{ mt: 4, display: 'inline-block', p: 3, bgcolor: '#e3f2fd', borderRadius: 2, color: '#1976d2' }}>
        <Typography fontWeight="bold">Coming Soon</Typography>
        <Typography variant="body2">This AI module is currently under development.</Typography>
      </Box>
    </Box>
  );
}

// =====================================================================
// MAIN APP
// =====================================================================
function App() {
  const [activeTab, setActiveTab] = useState('agent');

  // REPLACE the menuItems array in the App() function
  const menuItems = [
    { id: 'agent',        label: 'AI Agent',                      icon: <SmartToyIcon /> },   // ← NEW (first)
    // { id: 'new-module',   label: 'New Module Development',        icon: <AddBoxIcon /> },
    // { id: 'scoped-app',   label: 'Scoped App Development',        icon: <VpnKeyIcon /> },
    // { id: 'integrations', label: 'Integration & Modernization',   icon: <SyncAltIcon /> },
    // { id: 'tech-debt',    label: 'Technical Debt Clearance',      icon: <CleaningServicesIcon /> },
    // { id: 'release',      label: 'Release & Change Management',   icon: <RocketLaunchIcon /> },
  ];

  // REPLACE the renderContent function
  const renderContent = () => {
    switch (activeTab) {
      case 'agent':        return <AgentChat />;          // ← NEW
      case 'new-module':   return <NewModuleTool />;
      case 'scoped-app':   return <ScopedAppTool />;
      case 'tech-debt':    return <TechDebtTool />;
      case 'integrations': return <IntegrationTool />;
      case 'release':      return <ReleaseChangeTool />;
      default:             return <AgentChat />;          // ← default to agent now
    }
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', backgroundColor: '#f0f4f8' }}>
      <CssBaseline />

      {/* TOP BAR */}
      <AppBar position="fixed" sx={{ width: `calc(100% - ${drawerWidth}px)`, ml: `${drawerWidth}px`, bgcolor: 'white', color: 'black', boxShadow: 1 }}>
        <Toolbar>
          <Typography variant="h6" noWrap fontWeight="bold">
            {menuItems.find(item => item.id === activeTab)?.label}
          </Typography>
        </Toolbar>
      </AppBar>

      {/* SIDEBAR */}
      <Drawer
        sx={{
          width: drawerWidth, flexShrink: 0,
          '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box', bgcolor: '#1e293b', color: 'white' },
        }}
        variant="permanent" anchor="left"
      >
        <Toolbar sx={{ my: 2, px: 2 }}>
          <StorageIcon sx={{ mr: 1.5, color: '#3b82f6' }} />
          {/* Remove 'noWrap' if it is there, and slightly reduce font size */}
          <Typography 
            variant="h6" 
            fontWeight="bold" 
            sx={{ 
              fontSize: '1.1rem',  // slightly smaller font
              lineHeight: 1.2,     // tighter line spacing if it drops to two lines
              whiteSpace: 'normal' // forces it to wrap to a second line instead of cutting off
            }}
          >
            Automating ServiceNow
          </Typography>
        </Toolbar>
        <Divider sx={{ bgcolor: 'rgba(255,255,255,0.1)' }} />
        <Typography variant="overline" sx={{ px: 3, pt: 2, color: '#94a3b8' }}>Enterprise Services</Typography>
        <List sx={{ mt: 1 }}>
          {menuItems.map((item) => (
            <ListItem key={item.id} disablePadding>
              <ListItemButton
                selected={activeTab === item.id}
                onClick={() => setActiveTab(item.id)}
                sx={{
                  mx: 1, borderRadius: 1, mb: 0.5,
                  '&.Mui-selected': { bgcolor: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa' },
                  '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' }
                }}
              >
                <ListItemIcon sx={{ color: activeTab === item.id ? '#60a5fa' : '#94a3b8', minWidth: 40 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{ fontSize: '0.9rem', fontWeight: activeTab === item.id ? 'bold' : 'normal' }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Drawer>

      {/* MAIN CONTENT */}
      {/* ── UPDATE MAIN CONTENT CONTAINER IN APP.JSX ────────────────────────── */}
      <Box 
        component="main" 
        sx={{ 
          flexGrow: 1, 
          p: 4, 
          mt: 8, 
          width: `calc(100% - ${drawerWidth}px)`, // Spans the exact remaining space
          minHeight: 'calc(100vh - 64px)',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {renderContent()}
      </Box>
    </Box>
  );
}

export default App;