import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Button, Chip, Grid,
  CircularProgress, Alert, LinearProgress, Divider, Paper,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions,
  FormGroup, FormControlLabel, Checkbox, Tooltip, Accordion,
  AccordionSummary, AccordionDetails, TextField, Stepper,
  Step, StepLabel, StepContent
} from '@mui/material';
 
import PlayArrowIcon               from '@mui/icons-material/PlayArrow';
import ExpandMoreIcon              from '@mui/icons-material/ExpandMore';
import FilterListIcon              from '@mui/icons-material/FilterList';
import OpenInNewIcon               from '@mui/icons-material/OpenInNew';
import AutoFixHighIcon             from '@mui/icons-material/AutoFixHigh';
import SecurityIcon                from '@mui/icons-material/Security';
import AccountTreeIcon             from '@mui/icons-material/AccountTree';
import SpeedIcon                   from '@mui/icons-material/Speed';
import WarningAmberIcon            from '@mui/icons-material/WarningAmber';
import ErrorOutlinedIcon           from '@mui/icons-material/ErrorOutlined';
import InfoOutlinedIcon            from '@mui/icons-material/InfoOutlined';
import CheckCircleOutlinedIcon     from '@mui/icons-material/CheckCircleOutlined';
import IntegrationInstructionsIcon from '@mui/icons-material/IntegrationInstructions';
import HubIcon                     from '@mui/icons-material/Hub';
import LockIcon                    from '@mui/icons-material/Lock';
import ListAltIcon                 from '@mui/icons-material/ListAlt';
import ArrowForwardIcon            from '@mui/icons-material/ArrowForward';
import CheckCircleIcon             from '@mui/icons-material/CheckCircle';
import CancelIcon                  from '@mui/icons-material/Cancel';
import EditIcon                    from '@mui/icons-material/Edit';
import BuildIcon                   from '@mui/icons-material/Build';
import VisibilityIcon              from '@mui/icons-material/Visibility';
 
const API_BASE      = 'http://127.0.0.1:8000';
const SNOW_INSTANCE = 'https://abhrademo5.service-now.com';
 
// ─────────────────────────────────────────
// URGENCY / SCORE HELPERS
// ─────────────────────────────────────────
const URGENCY_COLOR = {
  Critical: { bg: '#fef2f2', border: '#fca5a5', text: '#dc2626', chip: 'error',   bar: '#dc2626' },
  High:     { bg: '#fff7ed', border: '#fed7aa', text: '#ea580c', chip: 'error',   bar: '#ea580c' },
  Medium:   { bg: '#fffbeb', border: '#fcd34d', text: '#d97706', chip: 'warning', bar: '#d97706' },
  Low:      { bg: '#f0fdf4', border: '#86efac', text: '#16a34a', chip: 'success', bar: '#16a34a' },
  None:     { bg: '#f0f9ff', border: '#7dd3fc', text: '#0284c7', chip: 'info',    bar: '#0284c7' },
};
 
const scoreColor = (s) =>
  s <= 30 ? '#dc2626' : s <= 50 ? '#ea580c' : s <= 70 ? '#d97706' : s <= 85 ? '#16a34a' : '#0284c7';
 
const ScoreGauge = ({ score }) => {
  const color = scoreColor(score);
  return (
    <Box sx={{ textAlign: 'center' }}>
      <Box sx={{
        width: 56, height: 56, borderRadius: '50%',
        border: `4px solid ${color}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        bgcolor: `${color}15`, mx: 'auto'
      }}>
        <Typography variant="body2" fontWeight="bold" sx={{ color }}>{score}</Typography>
      </Box>
      <Typography variant="caption" color="text.secondary">/100</Typography>
    </Box>
  );
};
 
const UrgencyChip = ({ urgency }) => {
  const cfg  = URGENCY_COLOR[urgency] || URGENCY_COLOR.None;
  const icons = { Critical: <ErrorOutlinedIcon />, High: <WarningAmberIcon />,
                  Medium: <WarningAmberIcon />, Low: <InfoOutlinedIcon />,
                  None: <CheckCircleOutlinedIcon /> };
  return (
    <Chip icon={icons[urgency] || icons.None} label={urgency || 'None'}
      size="small" color={cfg.chip} variant="filled"
      sx={{ fontWeight: 'bold', fontSize: '0.75rem' }} />
  );
};
 
const FlagBadge = ({ flag }) => {
  const color =
    flag.includes('credential') || flag.includes('auth') || flag.includes('soap') ? '#dc2626' :
    flag.includes('error')      || flag.includes('retry') || flag.includes('log')  ? '#d97706' :
    flag.includes('already_oauth2') ? '#16a34a' : '#64748b';
  return (
    <Chip label={flag} size="small" sx={{
      fontFamily: 'monospace', fontSize: '0.68rem',
      bgcolor: `${color}15`, color, border: `1px solid ${color}40`, height: 22
    }} />
  );
};
 
const StatCard = ({ label, value, color, icon, subtitle }) => (
  <Card elevation={0} sx={{
    border: `1px solid ${color}30`, borderTop: `4px solid ${color}`,
    borderRadius: 2, flex: 1, minWidth: 110
  }}>
    <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="h3" fontWeight="bold" sx={{ color, lineHeight: 1 }}>{value}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{label}</Typography>
          {subtitle && <Typography variant="caption" sx={{ color, fontWeight: 'bold' }}>{subtitle}</Typography>}
        </Box>
        <Box sx={{ color, opacity: 0.5, mt: 0.5 }}>{icon}</Box>
      </Box>
    </CardContent>
  </Card>
);
 
 
// ─────────────────────────────────────────
// BEFORE / AFTER COMPARISON ROW
// ─────────────────────────────────────────
const CompareRow = ({ before, after }) => (
  <Box sx={{
    display: 'grid', gridTemplateColumns: '1fr 40px 1fr',
    alignItems: 'center', gap: 1, mb: 1.5
  }}>
    {/* Before */}
    <Paper elevation={0} sx={{
      p: 1.5, borderRadius: 2,
      border: '1px solid #fca5a5', bgcolor: '#fef2f2',
      display: 'flex', alignItems: 'flex-start', gap: 1
    }}>
      <CancelIcon sx={{ color: '#dc2626', fontSize: 18, mt: 0.1, flexShrink: 0 }} />
      <Box>
        <Typography variant="caption" fontWeight="bold" color="#dc2626">{before.label}</Typography>
        <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>{before.value}</Typography>
      </Box>
    </Paper>
 
    {/* Arrow */}
    <Box sx={{ display: 'flex', justifyContent: 'center' }}>
      <ArrowForwardIcon sx={{ color: '#94a3b8', fontSize: 20 }} />
    </Box>
 
    {/* After */}
    <Paper elevation={0} sx={{
      p: 1.5, borderRadius: 2,
      border: '1px solid #86efac', bgcolor: '#f0fdf4',
      display: 'flex', alignItems: 'flex-start', gap: 1
    }}>
      <CheckCircleIcon sx={{ color: '#16a34a', fontSize: 18, mt: 0.1, flexShrink: 0 }} />
      <Box>
        <Typography variant="caption" fontWeight="bold" color="#16a34a">{after.label}</Typography>
        <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>{after.value}</Typography>
      </Box>
    </Paper>
  </Box>
);
 
 
// ─────────────────────────────────────────
// NEW COMPONENT CARD (shown in preview)
// ─────────────────────────────────────────
const NewComponentCard = ({ icon, color, title, name, details }) => (
  <Paper elevation={0} sx={{
    p: 2, borderRadius: 2,
    border: `1px solid ${color}40`, bgcolor: `${color}08`
  }}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
      <Box sx={{ color }}>{icon}</Box>
      <Typography variant="caption" fontWeight="bold" sx={{ color, textTransform: 'uppercase' }}>
        {title}
      </Typography>
    </Box>
    <Typography variant="body2" fontWeight="bold">{name}</Typography>
    {details && <Typography variant="caption" color="text.secondary">{details}</Typography>}
  </Paper>
);
 
 
// ─────────────────────────────────────────
// PREVIEW + APPLY DIALOG
// ─────────────────────────────────────────
export function ModernizeDialog({ finding, open, onClose, onApplied }) {
  const [phase,        setPhase]        = useState('idle');
  // phases: idle | loading_preview | preview | editing | applying | result
 
  const [blueprint,    setBlueprint]    = useState(null);
  const [previewError, setPreviewError] = useState(null);
  const [applyResult,  setApplyResult]  = useState(null);
 
  // Editable user inputs (pre-filled from blueprint)
  const [inputs, setInputs] = useState({
    new_rest_name:  '',
    new_endpoint:   '',
    new_flow_name:  '',
    new_auth_name:  '',
    auth_type:      'oauth2',
  });
 
  // Reset when dialog opens
  useEffect(() => {
    if (open && finding) {
      setPhase('idle');
      setBlueprint(null);
      setPreviewError(null);
      setApplyResult(null);
    }
  }, [open, finding]);
 
  // Pre-fill inputs when blueprint arrives
  useEffect(() => {
    if (blueprint) {
      setInputs({
        new_rest_name: blueprint.new_rest_message?.suggested_name  || `${finding?.name} v2`,
        new_endpoint:  blueprint.new_rest_message?.suggested_endpoint || '',
        new_flow_name: blueprint.new_flow?.suggested_name          || `${finding?.name} Flow`,
        new_auth_name: blueprint.new_auth_profile?.suggested_name  || `${finding?.name} Auth`,
        auth_type:     blueprint.new_rest_message?.suggested_auth  || 'oauth2',
      });
    }
  }, [blueprint]);
 
  if (!finding) return null;
 
  // ── FETCH PREVIEW ─────────────────────
  const loadPreview = async () => {
    setPhase('loading_preview');
    setPreviewError(null);
    try {
      const res = await fetch(`${API_BASE}/api/preview-modernization`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ finding }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setBlueprint(data.blueprint);
        setPhase('preview');
      } else {
        setPreviewError(data.message || 'Preview failed.');
        setPhase('idle');
      }
    } catch (err) {
      setPreviewError(err.message);
      setPhase('idle');
    }
  };
 
  // ── APPLY MODERNIZATION ───────────────
  const applyModernization = async () => {
    setPhase('applying');
    try {
      const res = await fetch(`${API_BASE}/api/apply-modernization`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ finding, blueprint, user_inputs: inputs }),
      });
      const data = await res.json();
      setApplyResult(data);
      setPhase('result');
      if (onApplied) onApplied(finding.sys_id, data);
    } catch (err) {
      setApplyResult({ status: 'failed', errors: [err.message], steps: [], created_records: [] });
      setPhase('result');
    }
  };
 
  const cfg = URGENCY_COLOR[finding.urgency] || URGENCY_COLOR.None;
 
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth
      PaperProps={{ sx: { borderRadius: 3, border: `2px solid ${cfg.border}` } }}>
 
      {/* ── HEADER ── */}
      <DialogTitle sx={{ bgcolor: cfg.bg, borderBottom: `1px solid ${cfg.border}`, pb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <AutoFixHighIcon sx={{ color: cfg.text }} />
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" fontWeight="bold">Modernize Integration</Typography>
            <Typography variant="caption" color="text.secondary">
              {finding.name} · {finding.table_source}
            </Typography>
          </Box>
          <ScoreGauge score={finding.modernization_score} />
          <UrgencyChip urgency={finding.urgency} />
        </Box>
      </DialogTitle>
 
      <DialogContent sx={{ pt: 3 }}>
 
        {/* ── PHASE: IDLE ── */}
        {phase === 'idle' && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <AutoFixHighIcon sx={{ fontSize: 56, color: '#3b82f6', mb: 2 }} />
            <Typography variant="h6" fontWeight="bold" sx={{ mb: 1 }}>
              Ready to Generate Modernization Preview
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 420, mx: 'auto' }}>
              AI will analyze this integration and generate a Before vs After
              comparison showing exactly what will change.
              <br /><strong>Nothing will be modified in ServiceNow yet.</strong>
            </Typography>
            {previewError && <Alert severity="error" sx={{ mb: 2 }}>{previewError}</Alert>}
            <Button variant="contained" size="large" startIcon={<VisibilityIcon />}
              onClick={loadPreview} sx={{ px: 5 }}>
              Generate Preview
            </Button>
          </Box>
        )}
 
        {/* ── PHASE: LOADING PREVIEW ── */}
        {phase === 'loading_preview' && (
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <CircularProgress size={50} sx={{ mb: 2 }} />
            <Typography variant="h6" color="text.secondary">
              AI is generating modernization preview...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Analyzing issues and designing the modern architecture
            </Typography>
          </Box>
        )}
 
        {/* ── PHASE: PREVIEW ── */}
        {(phase === 'preview' || phase === 'editing') && blueprint && (
          <Box>
            {/* Summary */}
            <Paper elevation={0} sx={{ p: 2, mb: 3, bgcolor: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 2 }}>
              <Typography variant="body2" fontWeight="medium">{blueprint.summary}</Typography>
            </Paper>
 
            {/* Before / After comparison */}
            <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1.5 }}>
              BEFORE → AFTER COMPARISON
            </Typography>
            {blueprint.before_state?.map((before, i) => (
              <CompareRow
                key={i}
                before={before}
                after={blueprint.after_state?.[i] || { label: before.label, value: 'Improved', status: 'good' }}
              />
            ))}
 
            <Divider sx={{ my: 3 }} />
 
            {/* New components that will be created */}
            <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1.5 }}>
              COMPONENTS THAT WILL BE CREATED
            </Typography>
            <Grid container spacing={2} sx={{ mb: 3 }}>
              {blueprint.create_rest_message && (
                <Grid item xs={12} md={4}>
                  <NewComponentCard
                    icon={<IntegrationInstructionsIcon />}
                    color="#3b82f6"
                    title="REST Message"
                    name={inputs.new_rest_name}
                    details={inputs.new_endpoint || 'Endpoint to be configured'}
                  />
                </Grid>
              )}
              {blueprint.create_auth_profile && (
                <Grid item xs={12} md={4}>
                  <NewComponentCard
                    icon={<LockIcon />}
                    color="#7c3aed"
                    title="Auth Profile"
                    name={inputs.new_auth_name}
                    details={`Type: ${inputs.auth_type}`}
                  />
                </Grid>
              )}
              {blueprint.create_flow && (
                <Grid item xs={12} md={4}>
                  <NewComponentCard
                    icon={<AccountTreeIcon />}
                    color="#16a34a"
                    title="Flow Designer Flow"
                    name={inputs.new_flow_name}
                    details="Created inactive — activate after adding steps"
                  />
                </Grid>
              )}
            </Grid>
 
            {/* Old record action */}
            <Paper elevation={0} sx={{ p: 2, mb: 3, bgcolor: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 2 }}>
              <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                <WarningAmberIcon sx={{ color: '#d97706', flexShrink: 0, mt: 0.2 }} />
                <Box>
                  <Typography variant="body2" fontWeight="bold" color="#d97706">
                    Old Record: Will be DEACTIVATED (not deleted)
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    "{finding.name}" → active = false after all new components are created.
                    {blueprint.old_record_reason && ` ${blueprint.old_record_reason}`}
                    {' '}Fully reversible from ServiceNow.
                  </Typography>
                </Box>
              </Box>
            </Paper>
 
            {/* Edit section */}
            {phase === 'editing' && (
              <Box>
                <Divider sx={{ mb: 2 }} />
                <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 2 }}>
                  EDIT SUGGESTED VALUES
                </Typography>
                <Grid container spacing={2}>
                  {blueprint.create_rest_message && (
                    <>
                      <Grid item xs={12} md={6}>
                        <TextField fullWidth size="small" label="New REST Message Name"
                          value={inputs.new_rest_name}
                          onChange={e => setInputs(p => ({ ...p, new_rest_name: e.target.value }))} />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField fullWidth size="small" label="Endpoint URL"
                          value={inputs.new_endpoint}
                          onChange={e => setInputs(p => ({ ...p, new_endpoint: e.target.value }))}
                          placeholder="https://api.example.com/v2" />
                      </Grid>
                    </>
                  )}
                  {blueprint.create_flow && (
                    <Grid item xs={12} md={6}>
                      <TextField fullWidth size="small" label="Flow Name"
                        value={inputs.new_flow_name}
                        onChange={e => setInputs(p => ({ ...p, new_flow_name: e.target.value }))} />
                    </Grid>
                  )}
                  {blueprint.create_auth_profile && (
                    <Grid item xs={12} md={6}>
                      <TextField fullWidth size="small" label="Auth Profile Name"
                        value={inputs.new_auth_name}
                        onChange={e => setInputs(p => ({ ...p, new_auth_name: e.target.value }))} />
                    </Grid>
                  )}
                </Grid>
              </Box>
            )}
          </Box>
        )}
 
        {/* ── PHASE: APPLYING ── */}
        {phase === 'applying' && (
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <CircularProgress size={50} sx={{ mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Applying Modernization...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Creating components in ServiceNow → then deactivating old record
            </Typography>
            <LinearProgress sx={{ maxWidth: 400, mx: 'auto', mt: 3, borderRadius: 4 }} />
          </Box>
        )}
 
        {/* ── PHASE: RESULT ── */}
        {phase === 'result' && applyResult && (
          <Box>
            {/* Overall status banner */}
            <Alert
              severity={applyResult.status === 'completed' ? 'success'
                      : applyResult.status === 'partial'   ? 'warning' : 'error'}
              sx={{ mb: 3 }}
            >
              {applyResult.status === 'completed' &&
                '✅ Modernization complete! All components created and old record deactivated.'}
              {applyResult.status === 'partial' &&
                '⚠️ Components created but old record deactivation had an issue. Review below.'}
              {applyResult.status === 'failed' &&
                '❌ Modernization failed. Old record was NOT deactivated — it remains active.'}
            </Alert>
 
            {/* Step results */}
            <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1.5 }}>
              STEPS
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
              {applyResult.steps?.map((step, i) => (
                <Paper key={i} elevation={0} sx={{
                  p: 1.5, borderRadius: 2,
                  border: `1px solid ${step.success ? '#86efac' : '#fca5a5'}`,
                  bgcolor: step.success ? '#f0fdf4' : '#fef2f2',
                  display: 'flex', alignItems: 'flex-start', gap: 1.5
                }}>
                  {step.success
                    ? <CheckCircleIcon sx={{ color: '#16a34a', fontSize: 20, flexShrink: 0, mt: 0.1 }} />
                    : <CancelIcon     sx={{ color: '#dc2626', fontSize: 20, flexShrink: 0, mt: 0.1 }} />
                  }
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" fontWeight="bold">{step.step}</Typography>
                    <Typography variant="caption" color="text.secondary">{step.message}</Typography>
                  </Box>
                  {step.sys_id && step.success && (
                    <Button size="small" variant="text" endIcon={<OpenInNewIcon sx={{ fontSize: 13 }} />}
                      onClick={() => window.open(`${SNOW_INSTANCE}/nav_to.do?uri=${step.snow_url}`, '_blank')}
                      sx={{ flexShrink: 0 }}>
                      Open
                    </Button>
                  )}
                </Paper>
              ))}
            </Box>
 
            {/* Created records links */}
            {applyResult.created_records?.length > 0 && (
              <Box>
                <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>
                  CREATED RECORDS
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {applyResult.created_records.map((rec, i) => (
                    <Button key={i} size="small" variant="outlined"
                      startIcon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
                      onClick={() => window.open(`${SNOW_INSTANCE}/nav_to.do?uri=${rec.snow_url}`, '_blank')}
                      sx={{ fontSize: '0.75rem' }}>
                      {rec.label}: {rec.name}
                    </Button>
                  ))}
                </Box>
              </Box>
            )}
          </Box>
        )}
 
      </DialogContent>
 
      {/* ── FOOTER ACTIONS ── */}
      <DialogActions sx={{ p: 2.5, borderTop: '1px solid #e2e8f0', gap: 1 }}>
        <Button onClick={onClose} variant="outlined" sx={{ mr: 'auto' }}>
          {phase === 'result' ? 'Close' : 'Cancel'}
        </Button>
 
        {/* Preview phase actions */}
        {(phase === 'preview' || phase === 'editing') && (
          <>
            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={() => setPhase(p => p === 'editing' ? 'preview' : 'editing')}
            >
              {phase === 'editing' ? 'Hide Edit' : 'Edit Values'}
            </Button>
            <Button
              variant="contained"
              color="success"
              startIcon={<BuildIcon />}
              onClick={applyModernization}
              sx={{ bgcolor: '#16a34a', '&:hover': { bgcolor: '#15803d' } }}
            >
              Approve & Build
            </Button>
          </>
        )}
 
        {/* Result phase — regenerate option */}
        {phase === 'result' && applyResult?.status !== 'completed' && (
          <Button variant="contained" onClick={() => { setPhase('idle'); setApplyResult(null); }}>
            Try Again
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
 
 
// ─────────────────────────────────────────
// DETAIL DIALOG  (scan findings detail)
// ─────────────────────────────────────────
function IntegrationDetailDialog({ finding, open, onClose, onModernizeClick }) {
  if (!finding) return null;
  const cfg = URGENCY_COLOR[finding.urgency] || URGENCY_COLOR.None;
 
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth
      PaperProps={{ sx: { borderRadius: 3, border: `2px solid ${cfg.border}` } }}>
 
      <DialogTitle sx={{ bgcolor: cfg.bg, borderBottom: `1px solid ${cfg.border}`, pb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <IntegrationInstructionsIcon sx={{ color: cfg.text }} />
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" fontWeight="bold">{finding.name}</Typography>
            <Typography variant="caption" color="text.secondary">
              {finding.label} · {finding.table_source}
            </Typography>
          </Box>
          <ScoreGauge score={finding.modernization_score} />
          <UrgencyChip urgency={finding.urgency} />
        </Box>
      </DialogTitle>
 
      <DialogContent sx={{ pt: 3 }}>
        <Grid container spacing={3}>
 
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>METADATA</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8 }}>
              {[
                ['Current Type',  finding.current_type || '—'],
                ['Active',        finding.active === 'true' || finding.active === true ? '✅ Yes' : '❌ No'],
                ['Last Updated',  finding.last_updated || '—'],
                ['Updated By',    finding.updated_by || '—'],
                ['Table',         finding.table_source],
              ].map(([k, v]) => (
                <Box key={k} sx={{ display: 'flex', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>{k}:</Typography>
                  <Typography variant="body2" fontWeight="medium">{v}</Typography>
                </Box>
              ))}
              {finding.extra && Object.entries(finding.extra).filter(([,v]) => v).map(([k, v]) => (
                <Box key={k} sx={{ display: 'flex', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary"
                    sx={{ minWidth: 120, textTransform: 'capitalize' }}>
                    {k.replace(/_/g,' ')}:
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">{String(v)}</Typography>
                </Box>
              ))}
            </Box>
          </Grid>
 
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>DETECTED FLAGS</Typography>
            {finding.basic_flags?.length > 0
              ? <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.8 }}>
                  {finding.basic_flags.map((f, i) => <FlagBadge key={i} flag={f} />)}
                </Box>
              : <Typography variant="body2" color="text.secondary">No flags detected</Typography>
            }
          </Grid>
 
          {finding.ai_summary && (
            <Grid item xs={12}>
              <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>AI SUMMARY</Typography>
              <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8fafc', borderRadius: 2, border: '1px solid #e2e8f0' }}>
                <Typography variant="body2">{finding.ai_summary}</Typography>
              </Paper>
            </Grid>
          )}
 
          {finding.ai_issues?.length > 0 && (
            <Grid item xs={12}>
              <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1.5 }}>ISSUES FOUND</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {finding.ai_issues.map((issue, i) => {
                  const ic = URGENCY_COLOR[issue.risk === 'High' ? 'Critical' : issue.risk === 'Medium' ? 'Medium' : 'Low'] || URGENCY_COLOR.Low;
                  return (
                    <Paper key={i} elevation={0} sx={{ p: 1.5, borderRadius: 2, border: `1px solid ${ic.border}`, bgcolor: ic.bg }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.3 }}>
                        <Typography variant="body2" fontWeight="bold" sx={{ color: ic.text }}>{issue.type}</Typography>
                        <Chip label={issue.risk} size="small" color={ic.chip} variant="outlined" sx={{ height: 20, fontSize: '0.68rem' }} />
                      </Box>
                      <Typography variant="body2">{issue.detail}</Typography>
                    </Paper>
                  );
                })}
              </Box>
            </Grid>
          )}
 
          {finding.recommended_approach && finding.recommended_approach !== 'No modernization needed.' && (
            <Grid item xs={12}>
              <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1 }}>RECOMMENDED APPROACH</Typography>
              <Paper elevation={0} sx={{ p: 2, bgcolor: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                  <AutoFixHighIcon sx={{ color: '#2563eb', mt: 0.2, flexShrink: 0 }} />
                  <Typography variant="body2" fontWeight="medium">{finding.recommended_approach}</Typography>
                </Box>
              </Paper>
            </Grid>
          )}
 
          {finding.flow_designer_opportunity && finding.flow_designer_opportunity !== 'Not applicable' && (
            <Grid item xs={12} md={6}>
              <Paper elevation={0} sx={{ p: 2, bgcolor: '#f0fdf4', border: '1px solid #86efac', borderRadius: 2, height: '100%' }}>
                <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                  <AccountTreeIcon sx={{ color: '#16a34a', fontSize: 20 }} />
                  <Typography variant="subtitle2" fontWeight="bold" color="#16a34a">FLOW DESIGNER</Typography>
                </Box>
                <Typography variant="body2">{finding.flow_designer_opportunity}</Typography>
              </Paper>
            </Grid>
          )}
 
          {finding.integrationhub_opportunity && finding.integrationhub_opportunity !== 'Not applicable' && (
            <Grid item xs={12} md={6}>
              <Paper elevation={0} sx={{ p: 2, bgcolor: '#faf5ff', border: '1px solid #d8b4fe', borderRadius: 2, height: '100%' }}>
                <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                  <HubIcon sx={{ color: '#7c3aed', fontSize: 20 }} />
                  <Typography variant="subtitle2" fontWeight="bold" color="#7c3aed">INTEGRATIONHUB</Typography>
                </Box>
                <Typography variant="body2">{finding.integrationhub_opportunity}</Typography>
              </Paper>
            </Grid>
          )}
 
          {finding.security_recommendation && finding.security_recommendation !== 'No changes needed' && (
            <Grid item xs={12}>
              <Paper elevation={0} sx={{ p: 2, bgcolor: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                  <LockIcon sx={{ color: '#ea580c', mt: 0.2, flexShrink: 0 }} />
                  <Box>
                    <Typography variant="subtitle2" fontWeight="bold" color="#ea580c" sx={{ mb: 0.5 }}>SECURITY</Typography>
                    <Typography variant="body2">{finding.security_recommendation}</Typography>
                  </Box>
                </Box>
              </Paper>
            </Grid>
          )}
        </Grid>
      </DialogContent>
 
      <DialogActions sx={{ p: 2.5, borderTop: '1px solid #e2e8f0', gap: 1 }}>
        <Button onClick={onClose} variant="outlined" sx={{ mr: 'auto' }}>Close</Button>
        <Button variant="outlined" startIcon={<OpenInNewIcon />}
          onClick={() => window.open(`${SNOW_INSTANCE}/nav_to.do?uri=${finding.table_source}.do?sys_id=${finding.sys_id}`, '_blank')}>
          Open in ServiceNow
        </Button>
        {finding.urgency !== 'None' && (
          <Button variant="contained" startIcon={<AutoFixHighIcon />}
            onClick={onModernizeClick}
            sx={{ bgcolor: '#7c3aed', '&:hover': { bgcolor: '#6d28d9' } }}>
            Preview Modernization
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

// ─────────────────────────────────────────
// MAIN: IntegrationTool
// ─────────────────────────────────────────
export default function IntegrationTool() {
  const [availableTables,  setAvailableTables]  = useState([]);
  const [selectedTables,   setSelectedTables]   = useState([]);
  const [limit,            setLimit]            = useState(50);
  const [loading,          setLoading]          = useState(false);
  const [loadingTables,    setLoadingTables]    = useState(true);
  const [result,           setResult]           = useState(null);
  const [error,            setError]            = useState(null);
  const [selectedFinding,  setSelectedFinding]  = useState(null);
  const [detailOpen,       setDetailOpen]       = useState(false);
  const [modernizeOpen,    setModernizeOpen]    = useState(false);
  const [urgencyFilter,    setUrgencyFilter]    = useState('All');
  const [modernizedIds,    setModernizedIds]    = useState(new Set());
 
  useEffect(() => {
    fetch(`${API_BASE}/api/integration-tables`)
      .then(r => r.json())
      .then(data => {
        setAvailableTables(data.tables || []);
        setSelectedTables((data.tables || []).map(t => t.table));
      })
      .catch(() => setError('Could not load table list from backend.'))
      .finally(() => setLoadingTables(false));
  }, []);
 
  const toggleTable = (table) =>
    setSelectedTables(prev =>
      prev.includes(table) ? prev.filter(t => t !== table) : [...prev, table]
    );
 
  const handleScan = async () => {
    if (!selectedTables.length) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/scan-integrations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tables: selectedTables, limit }),
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Scan failed'); }
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
 
  const openDetail    = (f) => { setSelectedFinding(f); setDetailOpen(true); };
  const openModernize = ()  => { setDetailOpen(false); setModernizeOpen(true); };
 
  const handleApplied = (sys_id, applyResult) => {
    if (applyResult.status === 'completed') {
      setModernizedIds(prev => new Set([...prev, sys_id]));
    }
  };
 
  const filteredFindings = result?.findings?.filter(f =>
    urgencyFilter === 'All' ? true : f.urgency === urgencyFilter
  ) || [];
 
  return (
    <Box sx={{ animation: 'fadeIn 0.4s ease-in' }}>
 
      {/* SCAN SETUP */}
      <Card elevation={0} sx={{ mb: 3, border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" fontWeight="bold" color="primary" sx={{ mb: 0.5 }}>
            Integration Modernization Scanner
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Scans for outdated REST scripts, SOAP messages, scheduled API jobs, and weak credentials.
            For each finding you can preview the modernization plan before applying any changes.
            <strong> Read-only scan — nothing is modified until you explicitly approve.</strong>
          </Typography>
 
          {loadingTables ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={18} />
              <Typography variant="body2" color="text.secondary">Loading tables...</Typography>
            </Box>
          ) : (
            <Grid container spacing={2}>
              {availableTables.map(t => (
                <Grid item xs={12} sm={6} md={4} key={t.table}>
                  <Paper elevation={0} sx={{
                    border: `1px solid ${selectedTables.includes(t.table) ? '#3b82f6' : '#e2e8f0'}`,
                    borderRadius: 2, p: 1.5,
                    bgcolor: selectedTables.includes(t.table) ? '#eff6ff' : 'white',
                    cursor: 'pointer', transition: 'all 0.15s',
                    '&:hover': { borderColor: '#3b82f6' }
                  }} onClick={() => !loading && toggleTable(t.table)}>
                    <FormControlLabel
                      control={
                        <Checkbox checked={selectedTables.includes(t.table)}
                          onChange={() => toggleTable(t.table)}
                          size="small" disabled={loading}
                          onClick={e => e.stopPropagation()} />
                      }
                      label={
                        <Box>
                          <Typography variant="body2" fontWeight="medium">{t.label}</Typography>
                          <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#94a3b8' }}>
                            {t.table}
                          </Typography>
                          {t.description && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                              {t.description}
                            </Typography>
                          )}
                        </Box>
                      }
                      sx={{ m: 0 }}
                    />
                  </Paper>
                </Grid>
              ))}
 
              <Grid item xs={12}>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Typography variant="body2" color="text.secondary">Records per table:</Typography>
                    <TextField type="number" size="small" value={limit}
                      onChange={e => setLimit(Number(e.target.value))}
                      disabled={loading} inputProps={{ min: 10, max: 200, step: 10 }}
                      sx={{ width: 90 }} />
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 'auto' }}>
                    <Chip label={`${selectedTables.length} selected`} size="small"
                      color={selectedTables.length > 0 ? 'primary' : 'default'} variant="outlined" />
                    <Button variant="contained" size="large" onClick={handleScan}
                      disabled={loading || !selectedTables.length}
                      startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <PlayArrowIcon />}
                      sx={{ px: 4 }}>
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
 
      {/* LOADING */}
      {loading && (
        <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2, p: 4, textAlign: 'center' }}>
          <CircularProgress size={50} sx={{ mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>Scanning Integrations...</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Reading ServiceNow → Detecting patterns → Running AI analysis
          </Typography>
          <LinearProgress sx={{ maxWidth: 400, mx: 'auto', borderRadius: 4 }} />
        </Card>
      )}
 
      {/* RESULTS */}
      {result && !loading && (
        <Box>
          {/* Stats */}
          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <StatCard label="Total Scanned"  value={result.summary.total_scanned} color="#3b82f6" icon={<ListAltIcon />} />
            <StatCard label="Critical"       value={result.summary.critical}      color="#dc2626" icon={<ErrorOutlinedIcon />} subtitle="Score 0–30" />
            <StatCard label="High"           value={result.summary.high}          color="#ea580c" icon={<WarningAmberIcon />} subtitle="Score 31–50" />
            <StatCard label="Medium"         value={result.summary.medium}        color="#d97706" icon={<InfoOutlinedIcon />} />
            <StatCard label="Low"            value={result.summary.low}           color="#16a34a" icon={<CheckCircleOutlinedIcon />} />
            <StatCard label="Already Modern" value={result.summary.already_modern} color="#0284c7" icon={<SpeedIcon />}
              subtitle={result.summary.avg_score > 0 ? `Avg: ${result.summary.avg_score}/100` : ''} />
          </Box>
 
          {/* Health bar */}
          {result.summary.avg_score > 0 && (
            <Card elevation={0} sx={{ mb: 3, border: '1px solid #e0e0e0', borderRadius: 2 }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight="bold" color="text.secondary">
                    INSTANCE MODERNIZATION HEALTH
                  </Typography>
                  <Typography variant="subtitle2" fontWeight="bold"
                    sx={{ color: scoreColor(result.summary.avg_score) }}>
                    {result.summary.avg_score}/100
                  </Typography>
                </Box>
                <LinearProgress variant="determinate" value={result.summary.avg_score}
                  sx={{ height: 12, borderRadius: 6, bgcolor: '#e2e8f0',
                    '& .MuiLinearProgress-bar': { bgcolor: scoreColor(result.summary.avg_score), borderRadius: 6 } }} />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                  <Typography variant="caption" color="text.secondary">0 — Severely Outdated</Typography>
                  <Typography variant="caption" color="text.secondary">100 — Fully Modern</Typography>
                </Box>
                <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {Object.entries(result.summary.by_table || {}).map(([t, c]) => (
                    <Chip key={t} label={`${t}: ${c}`} size="small" variant="outlined"
                      sx={{ fontFamily: 'monospace', fontSize: '0.72rem' }} />
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}
 
          {/* Filter */}
          <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <FilterListIcon sx={{ color: '#94a3b8', mr: 0.5 }} />
            {['All','Critical','High','Medium','Low','None'].map(u => {
              const counts = { All: result.findings.length, Critical: result.summary.critical,
                High: result.summary.high, Medium: result.summary.medium,
                Low: result.summary.low, None: result.summary.already_modern };
              const cfg = URGENCY_COLOR[u] || URGENCY_COLOR.None;
              return (
                <Button key={u} size="small"
                  variant={urgencyFilter === u ? 'contained' : 'outlined'}
                  onClick={() => setUrgencyFilter(u)}
                  sx={{ minWidth: 0, px: 2,
                    ...(urgencyFilter === u
                      ? { bgcolor: u === 'All' ? '#3b82f6' : cfg.bar, '&:hover': { bgcolor: cfg.bar } }
                      : { color: u === 'All' ? '#3b82f6' : cfg.text, borderColor: u === 'All' ? '#3b82f6' : cfg.border }) }}>
                  {u} ({counts[u] ?? 0})
                </Button>
              );
            })}
          </Box>
 
          {/* Table */}
          <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: '#f8fafc' }}>
                    {['Integration Name','Type','Score','Urgency','Flags','Approach',''].map(h => (
                      <TableCell key={h} sx={{ fontWeight: 'bold', fontSize: '0.75rem', color: '#64748b', py: 1.5 }}>
                        {h}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredFindings.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 5, color: '#94a3b8' }}>
                        No findings match this filter.
                      </TableCell>
                    </TableRow>
                  ) : filteredFindings.map((f, i) => {
                    const cfg         = URGENCY_COLOR[f.urgency] || URGENCY_COLOR.None;
                    const modernized  = modernizedIds.has(f.sys_id);
                    return (
                      <TableRow key={i} hover onClick={() => openDetail(f)}
                        sx={{
                          cursor: 'pointer',
                          bgcolor: modernized ? '#f0fdf4' : i % 2 === 0 ? 'white' : '#fafafa',
                          '&:hover': { bgcolor: `${cfg.bg} !important` },
                          borderLeft: `3px solid ${modernized ? '#16a34a' : cfg.bar}`,
                          opacity: modernized ? 0.8 : 1,
                        }}>
 
                        <TableCell sx={{ maxWidth: 190 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8 }}>
                            <Tooltip title={f.name}>
                              <Typography variant="body2" fontWeight="medium" noWrap sx={{ maxWidth: 150 }}>
                                {f.name}
                              </Typography>
                            </Tooltip>
                            {modernized && (
                              <Chip label="Modernized" size="small" color="success"
                                sx={{ height: 18, fontSize: '0.65rem' }} />
                            )}
                          </Box>
                          <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#94a3b8' }}>
                            {f.table_source}
                          </Typography>
                        </TableCell>
 
                        <TableCell>
                          <Chip label={f.label} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                        </TableCell>
 
                        <TableCell sx={{ minWidth: 100 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" fontWeight="bold"
                              sx={{ color: scoreColor(f.modernization_score), minWidth: 26 }}>
                              {f.modernization_score}
                            </Typography>
                            <LinearProgress variant="determinate" value={f.modernization_score}
                              sx={{ flex: 1, height: 6, borderRadius: 3, bgcolor: '#e2e8f0',
                                '& .MuiLinearProgress-bar': { bgcolor: scoreColor(f.modernization_score), borderRadius: 3 } }} />
                          </Box>
                        </TableCell>
 
                        <TableCell><UrgencyChip urgency={f.urgency} /></TableCell>
 
                        <TableCell sx={{ maxWidth: 180 }}>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.4 }}>
                            {f.basic_flags?.slice(0, 2).map((fl, fi) => <FlagBadge key={fi} flag={fl} />)}
                            {f.basic_flags?.length > 2 && (
                              <Chip label={`+${f.basic_flags.length - 2}`} size="small"
                                sx={{ height: 22, fontSize: '0.7rem' }} />
                            )}
                          </Box>
                        </TableCell>
 
                        <TableCell sx={{ maxWidth: 200 }}>
                          <Tooltip title={f.recommended_approach}>
                            <Typography variant="caption" color="text.secondary" noWrap
                              sx={{ maxWidth: 190, display: 'block' }}>
                              {f.recommended_approach || '—'}
                            </Typography>
                          </Tooltip>
                        </TableCell>
 
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <Button size="small" variant="text"
                              onClick={e => { e.stopPropagation(); openDetail(f); }}>
                              Details
                            </Button>
                            {f.urgency !== 'None' && !modernized && (
                              <Button size="small" variant="outlined"
                                startIcon={<AutoFixHighIcon sx={{ fontSize: 13 }} />}
                                onClick={e => { e.stopPropagation(); setSelectedFinding(f); setModernizeOpen(true); }}
                                sx={{ fontSize: '0.7rem', color: '#7c3aed', borderColor: '#7c3aed',
                                  '&:hover': { bgcolor: '#faf5ff', borderColor: '#7c3aed' } }}>
                                Modernize
                              </Button>
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
 
          {/* Raw JSON */}
          <Accordion elevation={0} sx={{ mt: 2, border: '1px solid #e0e0e0', borderRadius: '8px !important', '&:before': { display: 'none' } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight="bold" color="text.secondary">View Raw Scan Output (JSON)</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Paper sx={{ p: 2, backgroundColor: '#1e1e1e', color: '#a6e22e', overflowX: 'auto', maxHeight: '400px' }}>
                <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '12px' }}>
                  {JSON.stringify(result, null, 2)}
                </pre>
              </Paper>
            </AccordionDetails>
          </Accordion>
        </Box>
      )}
 
      {/* Detail Dialog */}
      <IntegrationDetailDialog
        finding={selectedFinding}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        onModernizeClick={openModernize}
      />
 
      {/* Modernize Dialog */}
      <ModernizeDialog
        finding={selectedFinding}
        open={modernizeOpen}
        onClose={() => setModernizeOpen(false)}
        onApplied={handleApplied}
      />
    </Box>
  );
}