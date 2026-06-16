// DiscoveryPanel.jsx
// Handles all 3 scenarios for New Module Development:
//   Scenario 1 — module doesn't exist    → full feature list, each card shows AI sample preview
//   Scenario 2 — module fully exists     → show live SN data, offer enhancements
//   Scenario 3 — module partially exists → ✅ implemented (live data) + ☐ missing (AI preview)
//
// Props:
//   moduleName              : string
//   onFeaturesSelected(keys): called when user confirms selection
//   onCancel()              : called when user cancels

import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Button, Card, CardContent, Chip,
  CircularProgress, Alert, Paper, Grid, Tooltip,
  LinearProgress, Collapse
} from '@mui/material';

import CheckCircleIcon  from '@mui/icons-material/CheckCircle';
import AddCircleIcon    from '@mui/icons-material/AddCircle';
import BuildCircleIcon  from '@mui/icons-material/BuildCircle';
import AutoAwesomeIcon  from '@mui/icons-material/AutoAwesome';
import StorageIcon      from '@mui/icons-material/Storage';
import GroupIcon        from '@mui/icons-material/Group';
import DynamicFormIcon  from '@mui/icons-material/DynamicForm';
import ListAltIcon      from '@mui/icons-material/ListAlt';
import LockIcon         from '@mui/icons-material/Lock';
import MenuIcon         from '@mui/icons-material/Menu';
import AccountTreeIcon  from '@mui/icons-material/AccountTree';
import EmailIcon        from '@mui/icons-material/Email';
import FactCheckIcon    from '@mui/icons-material/FactCheck';
import CodeIcon         from '@mui/icons-material/Code';
import LibraryBooksIcon from '@mui/icons-material/LibraryBooks';
import TuneIcon         from '@mui/icons-material/Tune';
import ShareIcon        from '@mui/icons-material/Share';
import Checkbox         from '@mui/material/Checkbox';

const API_BASE = 'http://127.0.0.1:8000';

const INFRASTRUCTURE_KEYS = ['application', 'app_menu', 'fields'];

// ── Feature config — label, description, icon, color, AI sample preview ─────
const FEATURE_CFG = {
  tables: {
    label: 'Tables & Fields',
    desc:  'Database tables and custom field definitions',
    color: '#3b82f6',
    icon:  <StorageIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => [
      `u_${name.toLowerCase().replace(/ /g,'_')} (table)`,
      '  u_name           string',
      '  u_status         string',
      '  u_created_date   glide_date',
      '  u_description    string',
    ],
  },
  fields: {
    label: 'Custom Fields',
    desc:  'Additional field definitions on existing tables',
    color: '#6366f1',
    icon:  <ListAltIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => [
      `On u_${name.toLowerCase().replace(/ /g,'_')}:`,
      '  u_priority       string',
      '  u_approved_by    string',
      '  u_resolved_date  glide_date',
    ],
  },
  roles: {
    label: 'Roles',
    desc:  'Access control roles for the module',
    color: '#f59e0b',
    icon:  <GroupIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => {
      const n = name.toLowerCase().replace(/ /g,'_');
      return [`u_${n}_user`, `u_${n}_manager`, `u_${n}_admin`];
    },
  },
  forms: {
    label: 'Forms',
    desc:  'Form layouts for data entry screens',
    color: '#8b5cf6',
    icon:  <DynamicFormIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => [
      `${name} Registration Form`,
      `  Fields: name, status, description`,
      `${name} Detail Form`,
      `  Fields: all + approver, notes`,
    ],
  },
  list_layouts: {
    label: 'List Layouts',
    desc:  'Column configurations for list views',
    color: '#06b6d4',
    icon:  <ListAltIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => [
      `${name} List:`,
      '  Columns: name, status, created_date',
      '  Sort: created_date DESC',
    ],
  },
  access_controls: {
    label: 'Access Controls',
    desc:  'ACL rules for read / write / create / delete',
    color: '#ef4444',
    icon:  <LockIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => {
      const n = name.toLowerCase().replace(/ /g,'_');
      return [
        `read   → u_${n}_user`,
        `write  → u_${n}_manager`,
        `create → u_${n}_manager`,
        `delete → u_${n}_admin`,
      ];
    },
  },
  navigation: {
    label: 'Navigation',
    desc:  'Left-menu navigation entries',
    color: '#64748b',
    icon:  <MenuIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => [
      `${name} > All Records`,
      `${name} > Create New`,
      `${name} > My Records`,
    ],
  },
  workflows: {
    label: 'Workflows',
    desc:  'Automated multi-step business processes',
    color: '#10b981',
    icon:  <AccountTreeIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => [
      `${name} Approval Workflow`,
      `  Begin → Submit → Review`,
      `       → Approve → Notify → End`,
      `       → Reject  → Notify → End`,
    ],
  },
  notifications: {
    label: 'Notifications',
    desc:  'Email alerts triggered by record changes',
    color: '#0ea5e9',
    icon:  <EmailIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => [
      `On Insert  → notify manager`,
      `On Approve → notify submitter`,
      `On Reject  → notify submitter`,
    ],
  },
  approvals: {
    label: 'Approvals',
    desc:  'Sign-off rules for record state changes',
    color: '#f97316',
    icon:  <FactCheckIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => {
      const n = name.toLowerCase().replace(/ /g,'_');
      return [
        `Condition: status = 'pending'`,
        `Approver:  u_${n}_manager`,
        `Action:    set status = 'approved'`,
      ];
    },
  },
  client_scripts: {
    label: 'Client Scripts',
    desc:  'Browser-side field validation and UI logic',
    color: '#7c3aed',
    icon:  <CodeIcon sx={{ fontSize: 16 }} />,
    samplePreview: () => [
      `onChange: validate required fields`,
      `onLoad:   hide fields by role`,
      `onSubmit: confirm before save`,
    ],
  },
  script_includes: {
    label: 'Script Includes',
    desc:  'Reusable server-side logic libraries',
    color: '#059669',
    icon:  <LibraryBooksIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => {
      const n = name.replace(/ /g,'');
      return [
        `${n}Utils.validateRecord()`,
        `${n}Utils.getActiveItems()`,
        `${n}Utils.sendAlerts()`,
      ];
    },
  },
  system_properties: {
    label: 'System Properties',
    desc:  'Configurable app-level settings',
    color: '#0891b2',
    icon:  <TuneIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => {
      const n = name.toLowerCase().replace(/ /g,'.');
      return [
        `${n}.approval_required = true`,
        `${n}.max_records       = 100`,
        `${n}.notify_on_create  = true`,
      ];
    },
  },
  relationships: {
    label: 'Relationships',
    desc:  'Table-to-table relationship definitions',
    color: '#dc2626',
    icon:  <ShareIcon sx={{ fontSize: 16 }} />,
    samplePreview: (name) => {
      const n = name.toLowerCase().replace(/ /g,'_');
      return [
        `u_${n} → u_${n}_detail  (1:N)`,
        `u_${n} → u_${n}_contact (1:N)`,
        `u_${n} → sys_user       (N:1)`,
      ];
    },
  },
};

const ALL_FEATURES = [
  'tables','roles','forms','list_layouts',
  'access_controls','navigation','workflows',
  'notifications','approvals','client_scripts',
  'script_includes','system_properties','relationships',
];

const SCENARIO_CFG = {
  1: {
    color:   '#6366f1', bg: '#eef2ff', border: '#a5b4fc',
    icon:    <AddCircleIcon />,
    title:   'Module Not Found',
    subtitle:'No existing implementation detected. Select the features you want to create from scratch.',
  },
  2: {
    color:   '#16a34a', bg: '#f0fdf4', border: '#86efac',
    icon:    <CheckCircleIcon />,
    title:   'Fully Implemented',
    subtitle:'This module is fully set up in ServiceNow. You can still add enhancements.',
  },
  3: {
    color:   '#d97706', bg: '#fffbeb', border: '#fcd34d',
    icon:    <BuildCircleIcon />,
    title:   'Partially Implemented',
    subtitle:'Some components already exist. Select missing features below to complete the module.',
  },
};

// ── Helper: extract readable preview lines from live SN data ─────────────────
function getLivePreview(key, implementedData) {
  const items = implementedData?.[key];
  if (!items || items.length === 0) return null;
 
  const lines = items.slice(0, 4).map(item => {
    // Guard: skip if item is null/undefined
    if (!item) return null;
 
    switch (key) {
      case 'application':
        return item.name
          ? `${item.name}  (${item.scope || 'no scope'})`
          : null;
 
      case 'app_menu':
        return item.title || item.name || null;
 
      case 'tables':
        return item.name && item.label
          ? `${item.name}  (${item.label})`
          : item.name || item.label || null;
 
      case 'fields':
        return item.field_name && item.type
          ? `${item.field_name}  ${item.type}`
          : item.field_name || item.field_label || null;
 
      case 'roles':
        return item.name || null;
 
      case 'forms':
        // sys_ui_section: title is the form name, name is the table name
        // Show "Form Title → table_name" for clarity
        if (item.title && item.title !== 'false' && item.title !== 'true') {
          return `${item.title}  →  ${item.name || ''}`;
        }
        if (item.name && item.name !== 'false' && item.name !== 'true') {
          return item.name;
        }
        return null;
 
      case 'list_layouts':
        return item.name || null;
 
      case 'access_controls':
        return item.operation && item.name
          ? `${item.operation}  on  ${item.name}`
          : item.name || null;
 
      case 'navigation':
        return item.title && item.table
          ? `${item.title}  →  ${item.table}`
          : item.title || item.table || null;
 
      case 'workflows':
        return item.name
          ? `${item.name}  [${item.active === 'true' ? 'active' : 'inactive'}]`
          : null;
 
      case 'notifications':
        return item.name && item.table
          ? `${item.name}  →  ${item.table}`
          : item.name || null;
 
      case 'approvals':
        return item.name || null;
 
      case 'client_scripts':
        return item.name && item.type
          ? `${item.name}  (${item.type})`
          : item.name || null;
 
      case 'script_includes':
        return item.name || null;
 
      case 'system_properties':
        return item.name && item.value !== undefined
          ? `${item.name} = ${item.value}`
          : item.name || null;
 
      case 'relationships':
        return item.parent && item.child
          ? `${item.parent}  →  ${item.child}`
          : item.name || null;
 
      default:
        // Safe fallback — never show raw boolean or sys_id
        const val = item.name || item.title || item.label;
        if (val && val !== 'true' && val !== 'false') return val;
        return null;
    }
  }).filter(Boolean);  // ← removes null entries
 
  if (lines.length === 0) return null;
  if (items.length > 4) lines.push(`  + ${items.length - 4} more...`);
  return lines;
}

// ── Single feature card ───────────────────────────────────────────────────────
function FeatureCard({ featureKey, moduleName, isChecked, isImplemented, implementedData, onToggle, readOnly }) {
  const [hovered, setHovered] = useState(false);
  const cfg = FEATURE_CFG[featureKey] || { label: featureKey, desc: '', color: '#64748b', icon: null, samplePreview: () => [] };

  const liveLines   = isImplemented ? getLivePreview(featureKey, implementedData) : null;
  const sampleLines = !isImplemented ? cfg.samplePreview(moduleName) : null;
  const previewLines = liveLines || sampleLines || [];
  const showPreview  = (hovered || isChecked) && previewLines.length > 0;

  const borderColor = isImplemented
    ? '#16a34a'
    : isChecked
    ? cfg.color
    : '#e2e8f0';

  const bgColor = isImplemented
    ? '#f0fdf4'
    : isChecked
    ? `${cfg.color}08`
    : 'white';

  return (
    <Paper
      elevation={0}
      onClick={() => !readOnly && onToggle(featureKey)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      sx={{
        p: 1.5,
        border: `1px solid ${borderColor}`,
        borderLeft: `3px solid ${borderColor}`,
        borderRadius: 1.5,
        cursor: readOnly ? 'default' : 'pointer',
        bgcolor: bgColor,
        transition: 'all 0.15s',
        '&:hover': readOnly ? {} : {
          borderColor: cfg.color,
          borderLeftColor: cfg.color,
          bgcolor: `${cfg.color}05`,
        },
      }}
    >
      {/* Top row: icon + label + badge */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 0.5 }}>

        {/* Icon circle */}
        <Box sx={{
          width: 28, height: 28, borderRadius: 1, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          bgcolor: isImplemented ? '#dcfce7' : isChecked ? `${cfg.color}15` : '#f1f5f9',
          color: isImplemented ? '#16a34a' : isChecked ? cfg.color : '#64748b',
        }}>
          {cfg.icon}
        </Box>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" fontWeight={isChecked || isImplemented ? 'bold' : 'medium'}
            sx={{ color: isImplemented ? '#15803d' : isChecked ? cfg.color : '#1e293b', lineHeight: 1.3 }}>
            {cfg.label}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.2, display: 'block', fontSize: '0.68rem' }}>
            {cfg.desc}
          </Typography>
        </Box>

        {/* Right badge */}
        {isImplemented ? (
          <Chip label="live" size="small" icon={<CheckCircleIcon sx={{ fontSize: '12px !important' }} />}
            sx={{ height: 20, fontSize: '0.65rem', fontWeight: 'bold',
                  bgcolor: '#dcfce7', color: '#15803d', border: '1px solid #86efac',
                  '& .MuiChip-icon': { color: '#15803d' } }} />
        ) : (
          <Checkbox checked={isChecked} size="small"
            sx={{ p: 0, flexShrink: 0, color: cfg.color, '&.Mui-checked': { color: cfg.color } }}
            onClick={e => e.stopPropagation()}
            onChange={() => onToggle(featureKey)} />
        )}
      </Box>

      {/* Preview box — shown on hover or when selected */}
      <Collapse in={showPreview}>
        <Box sx={{
          mt: 1,
          p: 1,
          bgcolor: isImplemented ? '#f0fdf4' : '#f8fafc',
          border: `1px solid ${isImplemented ? '#86efac' : '#e2e8f0'}`,
          borderRadius: 1,
        }}>
          <Typography variant="caption" sx={{
            display: 'block', mb: 0.3, fontWeight: 'bold', fontSize: '0.62rem',
            color: isImplemented ? '#15803d' : '#94a3b8',
            textTransform: 'uppercase', letterSpacing: '0.05em',
          }}>
            {isImplemented ? '✅ in servicenow' : '🔮 will be created'}
          </Typography>
          {previewLines.map((line, i) => (
            <Typography key={i} variant="caption" sx={{
              display: 'block', fontFamily: 'monospace', fontSize: '0.68rem',
              color: isImplemented ? '#166534' : '#475569',
              lineHeight: 1.6,
              pl: line.startsWith('  ') ? 1 : 0,
            }}>
              {line}
            </Typography>
          ))}
        </Box>
      </Collapse>
    </Paper>
  );
}

// ── Main DiscoveryPanel ───────────────────────────────────────────────────────
export default function DiscoveryPanel({ moduleName, onFeaturesSelected, onCancel }) {
  const [phase,    setPhase]    = useState('discovering');
  const [status,   setStatus]   = useState(null);
  const [error,    setError]    = useState(null);
  const [selected, setSelected] = useState([]);

  useEffect(() => {
    if (moduleName) runDiscovery();
  }, [moduleName]);

  const runDiscovery = async () => {
    setPhase('discovering');
    setError(null);
    setStatus(null);
    try {
      const res  = await fetch(`${API_BASE}/api/module-status`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ module_name: moduleName }),
      });
      const data = await res.json();
      setStatus(data);
      setPhase('results');

      // Pre-select defaults per scenario
      if (data.scenario === 1) {
        setSelected(['tables','roles','forms','navigation','workflows','notifications','approvals']);
      } else if (data.scenario === 2) {
        setSelected([]);
      } else {
        setSelected(data.missing_keys || []);
      }
    } catch (err) {
      setError(err.message);
      setPhase('results');
    }
  };

  const toggleFeature = (key) =>
    setSelected(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);

  const selectableKeys = status?.scenario === 3
    ? (status.missing_keys || []).filter(k => !INFRASTRUCTURE_KEYS.includes(k))
    : ALL_FEATURES.filter(k => !INFRASTRUCTURE_KEYS.includes(k));

  const handleConfirm = () => {
    if (selected.length > 0) onFeaturesSelected(selected);
  };

  const scenarioCfg = status ? SCENARIO_CFG[status.scenario] : null;
  const pct         = status?.summary?.completion_percent ?? 0;

  // ── Discovering ──────────────────────────────────────────────────────────
  if (phase === 'discovering') {
    return (
      <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 2, p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1.5 }}>
          <CircularProgress size={22} />
          <Box>
            <Typography variant="body1" fontWeight="medium">
              Scanning ServiceNow for "{moduleName}"...
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Checking tables, roles, workflows, forms, navigation and more
            </Typography>
          </Box>
        </Box>
        <LinearProgress sx={{ borderRadius: 4, height: 4 }} />
      </Card>
    );
  }

  if (error) {
    return (
      <Alert severity="error" action={<Button size="small" onClick={runDiscovery}>Retry</Button>}>
        Discovery failed: {error}
      </Alert>
    );
  }

  return (
    <Box>

      {/* ── Scenario banner ── */}
      {scenarioCfg && (
        <Paper elevation={0} sx={{
          p: 2, mb: 2.5,
          bgcolor: scenarioCfg.bg,
          border: `1px solid ${scenarioCfg.border}`,
          borderLeft: `4px solid ${scenarioCfg.color}`,
          borderRadius: 2,
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
            <Box sx={{ color: scenarioCfg.color }}>{scenarioCfg.icon}</Box>
            <Typography variant="subtitle1" fontWeight="bold" sx={{ color: scenarioCfg.color }}>
              Scenario {status.scenario}: {scenarioCfg.title}
            </Typography>
            <Chip label={`${pct}% complete`} size="small"
              sx={{ ml: 'auto', bgcolor: scenarioCfg.color, color: '#fff', fontWeight: 'bold' }} />
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {scenarioCfg.subtitle}
          </Typography>
          {/* Completion progress bar */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <LinearProgress variant="determinate" value={pct}
              sx={{ flex: 1, height: 6, borderRadius: 3, bgcolor: '#e2e8f0',
                '& .MuiLinearProgress-bar': { bgcolor: scenarioCfg.color, borderRadius: 3 } }} />
            <Typography variant="caption" fontWeight="bold" sx={{ color: scenarioCfg.color, minWidth: 36 }}>
              {pct}%
            </Typography>
          </Box>
        </Paper>
      )}

      {/* ── Scenario 3: implemented cards (read-only with live data) ── */}
      {status?.scenario === 3 && status.implemented_keys?.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="caption" fontWeight="bold" color="text.secondary"
            sx={{ display: 'block', mb: 1.5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            ✅ Already implemented ({status.implemented_keys.length}) — hover to see live data
          </Typography>
          <Grid container spacing={1.5}>
            {status.implemented_keys.map(key => (
              <Grid item xs={12} sm={6} md={4} key={key}>
                <FeatureCard
                  featureKey={key}
                  moduleName={moduleName}
                  isChecked={false}
                  isImplemented={true}
                  implementedData={status.implemented}
                  onToggle={() => {}}
                  readOnly={true}
                />
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* ── Scenario 2: all implemented (read-only) ── */}
      {status?.scenario === 2 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="caption" fontWeight="bold" color="text.secondary"
            sx={{ display: 'block', mb: 1.5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            ✅ Fully implemented — hover any card to see live servicenow data
          </Typography>
          <Grid container spacing={1.5}>
            {status.implemented_keys?.map(key => (
              <Grid item xs={12} sm={6} md={4} key={key}>
                <FeatureCard
                  featureKey={key}
                  moduleName={moduleName}
                  isChecked={false}
                  isImplemented={true}
                  implementedData={status.implemented}
                  onToggle={() => {}}
                  readOnly={true}
                />
              </Grid>
            ))}
          </Grid>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1.5, display: 'block' }}>
            You can still select additional components below to enhance this module.
          </Typography>
        </Box>
      )}

      {/* ── Selectable features (missing / all) ── */}
      <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 2, mb: 2 }}>
        <CardContent sx={{ p: 2.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" fontWeight="bold" color="text.secondary"
              sx={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {status?.scenario === 3
                ? `❌ Missing — select to build (${selectableKeys.length} available)`
                : status?.scenario === 2
                ? 'Select enhancements to add'
                : 'Select features to create — hover to preview'
              }
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button size="small" variant="text"
                onClick={() => setSelected([...selectableKeys])}
                sx={{ fontSize: '0.7rem', color: '#6366f1', minWidth: 0 }}>
                All
              </Button>
              <Button size="small" variant="text"
                onClick={() => setSelected([])}
                sx={{ fontSize: '0.7rem', color: '#94a3b8', minWidth: 0 }}>
                Clear
              </Button>
            </Box>
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
            Hover a card to preview what will be created. Click to select.
          </Typography>

          {selectableKeys.length === 0 ? (
            <Alert severity="success">
              All standard features are already implemented. No missing features to add.
            </Alert>
          ) : (
            <Grid container spacing={1.5}>
              {selectableKeys.map(key => (
                <Grid item xs={12} sm={6} md={4} key={key}>
                  <FeatureCard
                    featureKey={key}
                    moduleName={moduleName}
                    isChecked={selected.includes(key)}
                    isImplemented={false}
                    implementedData={status?.implemented}
                    onToggle={toggleFeature}
                    readOnly={false}
                  />
                </Grid>
              ))}
            </Grid>
          )}
        </CardContent>
      </Card>

      {/* ── Action bar ── */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Chip
          label={`${selected.length} feature${selected.length !== 1 ? 's' : ''} selected`}
          size="small"
          color={selected.length > 0 ? 'primary' : 'default'}
          variant="outlined"
          sx={{ fontWeight: 'bold' }}
        />
        <Button variant="outlined" onClick={onCancel}
          sx={{ color: '#64748b', borderColor: '#e2e8f0' }}>
          Cancel
        </Button>
        <Button
          variant="contained"
          startIcon={<AutoAwesomeIcon />}
          onClick={handleConfirm}
          disabled={selected.length === 0}
          sx={{
            bgcolor: '#6366f1',
            '&:hover': { bgcolor: '#4f46e5' },
            '&:disabled': { bgcolor: '#e2e8f0', color: '#94a3b8' },
          }}
        >
          Generate Blueprint for {selected.length} Feature{selected.length !== 1 ? 's' : ''}
        </Button>
      </Box>
    </Box>
  );
}