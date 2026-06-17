// BlueprintPreview.jsx
// Full human-friendly blueprint breakdown — covers all 13 component types.

import React, { useState } from 'react';
import {
  Box, Typography, Paper, Chip, Grid, Divider,
  Collapse, Tooltip, Card, CardContent
} from '@mui/material';

import StorageIcon        from '@mui/icons-material/Storage';
import GroupIcon          from '@mui/icons-material/Group';
import DynamicFormIcon    from '@mui/icons-material/DynamicForm';
import AccountTreeIcon    from '@mui/icons-material/AccountTree';
import EmailIcon          from '@mui/icons-material/Email';
import FactCheckIcon      from '@mui/icons-material/FactCheck';
import MenuIcon           from '@mui/icons-material/Menu';
import LockIcon           from '@mui/icons-material/Lock';
import ListAltIcon        from '@mui/icons-material/ListAlt';
import CodeIcon           from '@mui/icons-material/Code';
import LibraryBooksIcon   from '@mui/icons-material/LibraryBooks';
import TuneIcon           from '@mui/icons-material/Tune';
import ShareIcon          from '@mui/icons-material/Share';
import ExpandMoreIcon     from '@mui/icons-material/ExpandMore';
import ExpandLessIcon     from '@mui/icons-material/ExpandLess';

// ── Field type → friendly label ──────────────────────────────────────────────
const TYPE_LABEL = {
  string:     { label: 'Text',    color: '#3b82f6' },
  integer:    { label: 'Number',  color: '#8b5cf6' },
  boolean:    { label: 'Yes/No',  color: '#10b981' },
  glide_date: { label: 'Date',    color: '#f59e0b' },
};

// ── Section config ────────────────────────────────────────────────────────────
const SECTION_CFG = {
  tables:            { icon: <StorageIcon />,      color: '#3b82f6', title: 'Tables & Fields',      desc: 'Database tables that will store your data' },
  roles:             { icon: <GroupIcon />,         color: '#f59e0b', title: 'Roles',                desc: 'Access control roles that will be created' },
  forms:             { icon: <DynamicFormIcon />,   color: '#8b5cf6', title: 'Forms',                desc: 'Form layouts users will see when editing records' },
  workflows:         { icon: <AccountTreeIcon />,   color: '#10b981', title: 'Workflows',            desc: 'Automated processes that trigger on record changes' },
  notifications:     { icon: <EmailIcon />,         color: '#0ea5e9', title: 'Notifications',        desc: 'Email alerts that will be sent automatically' },
  approvals:         { icon: <FactCheckIcon />,     color: '#f97316', title: 'Approvals',            desc: 'Sign-off rules that gate record state changes' },
  navigation:        { icon: <MenuIcon />,          color: '#64748b', title: 'Navigation Modules',   desc: 'Left-menu entries users will see' },
  access_controls:   { icon: <LockIcon />,          color: '#ef4444', title: 'Access Controls',      desc: 'ACL rules controlling who can read/write/create/delete' },
  list_layouts:      { icon: <ListAltIcon />,       color: '#06b6d4', title: 'List Layouts',         desc: 'Column configurations for list views' },
  client_scripts:    { icon: <CodeIcon />,          color: '#7c3aed', title: 'Client Scripts',       desc: 'Browser-side scripts for field validation and UI logic' },
  script_includes:   { icon: <LibraryBooksIcon />,  color: '#059669', title: 'Script Includes',      desc: 'Reusable server-side logic libraries' },
  system_properties: { icon: <TuneIcon />,          color: '#0891b2', title: 'System Properties',    desc: 'Configurable settings for the module' },
  relationships:     { icon: <ShareIcon />,         color: '#dc2626', title: 'Relationships',        desc: 'Table-to-table relationship definitions' },
};

// ── Section header ────────────────────────────────────────────────────────────
function SectionHeader({ sectionKey, count, expanded, onToggle }) {
  const cfg = SECTION_CFG[sectionKey] || { icon: null, color: '#64748b', title: sectionKey, desc: '' };
  return (
    <Box onClick={onToggle} sx={{
      display: 'flex', alignItems: 'center', gap: 1.5,
      p: 1.5, cursor: 'pointer', borderRadius: 1.5,
      '&:hover': { bgcolor: `${cfg.color}08` },
      transition: 'background 0.12s',
    }}>
      <Box sx={{
        width: 32, height: 32, borderRadius: 1, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        bgcolor: `${cfg.color}15`, color: cfg.color,
        '& svg': { fontSize: 18 },
      }}>
        {cfg.icon}
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" fontWeight="bold" sx={{ color: cfg.color }}>
            {cfg.title}
          </Typography>
          <Chip label={count} size="small" sx={{
            height: 18, fontSize: '0.65rem', fontWeight: 'bold',
            bgcolor: `${cfg.color}15`, color: cfg.color, border: `1px solid ${cfg.color}30`
          }} />
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.68rem' }}>
          {cfg.desc}
        </Typography>
      </Box>
      <Box sx={{ color: '#94a3b8', flexShrink: 0 }}>
        {expanded ? <ExpandLessIcon sx={{ fontSize: 18 }} /> : <ExpandMoreIcon sx={{ fontSize: 18 }} />}
      </Box>
    </Box>
  );
}

// ── Tables ────────────────────────────────────────────────────────────────────
function TablesBody({ tables }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, px: 1.5, pb: 1.5 }}>
      {tables.map((table, i) => (
        <Paper key={i} elevation={0} sx={{ p: 1.5, border: '1px solid #e2e8f0', borderRadius: 1.5, borderLeft: '3px solid #3b82f6' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="body2" fontWeight="bold">{table.table_label}</Typography>
            <Typography variant="caption" sx={{ fontFamily: 'monospace', bgcolor: '#f1f5f9', px: 0.8, py: 0.2, borderRadius: 0.5, color: '#64748b', fontSize: '0.68rem' }}>
              {table.table_name}
            </Typography>
          </Box>
          {table.fields?.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.6 }}>
              {table.fields.map((field, fi) => {
                const typeCfg = TYPE_LABEL[field.internal_type] || { label: field.internal_type, color: '#64748b' };
                return (
                  <Tooltip key={fi} title={`${field.field_name} · ${field.internal_type}`}>
                    <Chip size="small"
                      label={<Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <span>{field.field_label}</span>
                        <Box component="span" sx={{ fontSize: '0.58rem', bgcolor: `${typeCfg.color}20`, color: typeCfg.color, px: 0.5, borderRadius: 0.4, fontWeight: 'bold' }}>
                          {typeCfg.label}
                        </Box>
                      </Box>}
                      sx={{ height: 22, fontSize: '0.7rem', bgcolor: '#f8fafc', border: '1px solid #e2e8f0', '& .MuiChip-label': { px: 0.8 } }}
                    />
                  </Tooltip>
                );
              })}
            </Box>
          )}
        </Paper>
      ))}
    </Box>
  );
}

// ── Roles ─────────────────────────────────────────────────────────────────────
function RolesBody({ roles }) {
  const ROLE_DESC = { user: 'Can view and create records', manager: 'Can approve and manage records', admin: 'Full access including delete', viewer: 'Read-only access', approver: 'Can approve pending records' };
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, px: 1.5, pb: 1.5 }}>
      {roles.map((role, i) => {
        const name   = typeof role === 'string' ? role : role.name || '';
        const suffix = Object.keys(ROLE_DESC).find(k => name.toLowerCase().includes(k));
        return (
          <Paper key={i} elevation={0} sx={{ px: 1.5, py: 1, border: '1px solid #fde68a', borderLeft: '3px solid #f59e0b', borderRadius: 1.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <GroupIcon sx={{ fontSize: 16, color: '#f59e0b', flexShrink: 0 }} />
            <Box>
              <Typography variant="body2" fontWeight="bold" sx={{ fontFamily: 'monospace', color: '#92400e' }}>{name}</Typography>
              {suffix && <Typography variant="caption" color="text.secondary">{ROLE_DESC[suffix]}</Typography>}
            </Box>
          </Paper>
        );
      })}
    </Box>
  );
}

// ── Forms ─────────────────────────────────────────────────────────────────────
function FormsBody({ forms }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, px: 1.5, pb: 1.5 }}>
      {forms.map((form, i) => (
        <Paper key={i} elevation={0} sx={{ p: 1.5, border: '1px solid #ddd6fe', borderLeft: '3px solid #8b5cf6', borderRadius: 1.5 }}>
          <Typography variant="body2" fontWeight="bold" sx={{ color: '#5b21b6', mb: 0.8 }}>{form.form_name}</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">Table:</Typography>
            <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#64748b' }}>{form.target_table}</Typography>
          </Box>
          {form.visible_fields?.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
              <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center', mr: 0.5 }}>Fields:</Typography>
              {form.visible_fields.map((f, fi) => (
                <Chip key={fi} label={f} size="small" sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#f5f3ff', color: '#5b21b6', border: '1px solid #ddd6fe' }} />
              ))}
            </Box>
          )}
        </Paper>
      ))}
    </Box>
  );
}

// ── Workflows ─────────────────────────────────────────────────────────────────
function WorkflowsBody({ workflows }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, px: 1.5, pb: 1.5 }}>
      {workflows.map((wf, i) => (
        <Paper key={i} elevation={0} sx={{ p: 1.5, border: '1px solid #a7f3d0', borderLeft: '3px solid #10b981', borderRadius: 1.5 }}>
          <Typography variant="body2" fontWeight="bold" sx={{ color: '#065f46', mb: 0.8 }}>{wf.name}</Typography>
          {wf.trigger && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, mb: 1 }}>
              <Typography variant="caption" color="text.secondary">Triggers:</Typography>
              <Chip label={wf.trigger} size="small" sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#ecfdf5', color: '#065f46', border: '1px solid #a7f3d0' }} />
            </Box>
          )}
          {wf.steps?.length > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5 }}>
              {wf.steps.map((step, si) => (
                <React.Fragment key={si}>
                  <Chip label={step} size="small" sx={{ height: 22, fontSize: '0.68rem', bgcolor: '#f0fdf4', color: '#166534', border: '1px solid #86efac', fontWeight: 'medium' }} />
                  {si < wf.steps.length - 1 && <Typography sx={{ color: '#86efac', fontSize: '0.8rem', fontWeight: 'bold' }}>→</Typography>}
                </React.Fragment>
              ))}
            </Box>
          )}
        </Paper>
      ))}
    </Box>
  );
}

// ── Notifications ─────────────────────────────────────────────────────────────
function NotificationsBody({ notifications }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, px: 1.5, pb: 1.5 }}>
      {notifications.map((notif, i) => (
        <Paper key={i} elevation={0} sx={{ px: 1.5, py: 1, border: '1px solid #bae6fd', borderLeft: '3px solid #0ea5e9', borderRadius: 1.5 }}>
          <Typography variant="body2" fontWeight="bold" sx={{ color: '#0c4a6e', mb: 0.5 }}>{notif.name}</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {notif.trigger && (
              <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary">Trigger:</Typography>
                <Chip label={notif.trigger} size="small" sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#e0f2fe', color: '#0369a1', border: '1px solid #bae6fd' }} />
              </Box>
            )}
            {(notif.recipient || notif.recipient_role) && (
              <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary">To:</Typography>
                <Chip label={notif.recipient || notif.recipient_role} size="small" sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#e0f2fe', color: '#0369a1', border: '1px solid #bae6fd' }} />
              </Box>
            )}
          </Box>
        </Paper>
      ))}
    </Box>
  );
}

// ── Approvals ─────────────────────────────────────────────────────────────────
function ApprovalsBody({ approvals }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, px: 1.5, pb: 1.5 }}>
      {approvals.map((appr, i) => (
        <Paper key={i} elevation={0} sx={{ p: 1.5, border: '1px solid #fed7aa', borderLeft: '3px solid #f97316', borderRadius: 1.5 }}>
          <Typography variant="body2" fontWeight="bold" sx={{ color: '#9a3412', mb: 0.8 }}>{appr.name}</Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.4 }}>
            {appr.condition && (
              <Box sx={{ display: 'flex', gap: 0.8 }}>
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 72 }}>Condition:</Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#475569' }}>{appr.condition}</Typography>
              </Box>
            )}
            {appr.approver_role && (
              <Box sx={{ display: 'flex', gap: 0.8, alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 72 }}>Approver:</Typography>
                <Chip label={appr.approver_role} size="small" sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#fff7ed', color: '#9a3412', border: '1px solid #fed7aa' }} />
              </Box>
            )}
          </Box>
        </Paper>
      ))}
    </Box>
  );
}

// ── Navigation ────────────────────────────────────────────────────────────────
function NavigationBody({ items }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8, px: 1.5, pb: 1.5 }}>
      {items.map((item, i) => (
        <Paper key={i} elevation={0} sx={{ px: 1.5, py: 1, border: '1px solid #e2e8f0', borderLeft: '3px solid #64748b', borderRadius: 1.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <MenuIcon sx={{ fontSize: 14, color: '#64748b', flexShrink: 0 }} />
          <Box>
            <Typography variant="body2" fontWeight="bold" sx={{ color: '#334155' }}>{item.title || item}</Typography>
            {item.table && <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#94a3b8' }}>→ {item.table}</Typography>}
          </Box>
          {item.order && <Chip label={`order: ${item.order}`} size="small" sx={{ ml: 'auto', height: 16, fontSize: '0.6rem', bgcolor: '#f8fafc', color: '#94a3b8' }} />}
        </Paper>
      ))}
    </Box>
  );
}

// ── Access Controls ───────────────────────────────────────────────────────────
function AccessControlsBody({ acls }) {
  const OP_COLOR = { read: '#3b82f6', write: '#f59e0b', create: '#10b981', delete: '#ef4444' };
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8, px: 1.5, pb: 1.5 }}>
      {acls.map((acl, i) => {
        const opColor = OP_COLOR[acl.operation?.toLowerCase()] || '#64748b';
        return (
          <Paper key={i} elevation={0} sx={{ px: 1.5, py: 1, border: `1px solid ${opColor}30`, borderLeft: `3px solid ${opColor}`, borderRadius: 1.5 }}>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
              <Chip label={acl.operation?.toUpperCase()} size="small" sx={{ height: 18, fontSize: '0.65rem', fontWeight: 'bold', bgcolor: `${opColor}15`, color: opColor, border: `1px solid ${opColor}40` }} />
              <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#475569' }}>on {acl.table}</Typography>
              {acl.role && <>
                <Typography variant="caption" color="text.secondary">→</Typography>
                <Chip label={acl.role} size="small" sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#fff7ed', color: '#9a3412', border: '1px solid #fed7aa' }} />
              </>}
            </Box>
            {acl.description && <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.3 }}>{acl.description}</Typography>}
          </Paper>
        );
      })}
    </Box>
  );
}

// ── List Layouts ──────────────────────────────────────────────────────────────
function ListLayoutsBody({ layouts }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, px: 1.5, pb: 1.5 }}>
      {layouts.map((layout, i) => (
        <Paper key={i} elevation={0} sx={{ p: 1.5, border: '1px solid #a5f3fc', borderLeft: '3px solid #06b6d4', borderRadius: 1.5 }}>
          <Typography variant="body2" fontWeight="bold" sx={{ fontFamily: 'monospace', color: '#164e63', mb: 0.8 }}>{layout.table_name}</Typography>
          {layout.columns?.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center', mr: 0.5 }}>Columns:</Typography>
              {layout.columns.map((col, ci) => (
                <Chip key={ci} label={col} size="small" sx={{ height: 18, fontSize: '0.65rem', fontFamily: 'monospace', bgcolor: '#ecfeff', color: '#164e63', border: '1px solid #a5f3fc' }} />
              ))}
            </Box>
          )}
        </Paper>
      ))}
    </Box>
  );
}

// ── Client Scripts ────────────────────────────────────────────────────────────
function ClientScriptsBody({ scripts }) {
  const TYPE_COLOR = { onLoad: '#7c3aed', onChange: '#9333ea', onSubmit: '#6d28d9', onCellEdit: '#5b21b6' };
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, px: 1.5, pb: 1.5 }}>
      {scripts.map((cs, i) => {
        const typeColor = TYPE_COLOR[cs.type] || '#7c3aed';
        return (
          <Paper key={i} elevation={0} sx={{ p: 1.5, border: '1px solid #ddd6fe', borderLeft: '3px solid #7c3aed', borderRadius: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.8, flexWrap: 'wrap' }}>
              <Typography variant="body2" fontWeight="bold" sx={{ color: '#4c1d95' }}>{cs.name}</Typography>
              <Chip label={cs.type} size="small" sx={{ height: 18, fontSize: '0.65rem', fontWeight: 'bold', bgcolor: `${typeColor}15`, color: typeColor, border: `1px solid ${typeColor}40` }} />
              {cs.table && <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#94a3b8', fontSize: '0.65rem' }}>on {cs.table}</Typography>}
            </Box>
            {cs.field_name && (
              <Box sx={{ display: 'flex', gap: 0.8, mb: 0.5 }}>
                <Typography variant="caption" color="text.secondary">Field:</Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#64748b' }}>{cs.field_name}</Typography>
              </Box>
            )}
            {cs.script && (
              <Box sx={{ mt: 0.8, p: 1, bgcolor: '#1e293b', borderRadius: 1, overflowX: 'auto' }}>
                <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#a6e22e', fontSize: '0.65rem', whiteSpace: 'pre-wrap', display: 'block' }}>
                  {cs.script.length > 120 ? cs.script.slice(0, 120) + '...' : cs.script}
                </Typography>
              </Box>
            )}
          </Paper>
        );
      })}
    </Box>
  );
}

// ── Script Includes ───────────────────────────────────────────────────────────
function ScriptIncludesBody({ includes }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, px: 1.5, pb: 1.5 }}>
      {includes.map((si, i) => (
        <Paper key={i} elevation={0} sx={{ p: 1.5, border: '1px solid #a7f3d0', borderLeft: '3px solid #059669', borderRadius: 1.5 }}>
          <Typography variant="body2" fontWeight="bold" sx={{ fontFamily: 'monospace', color: '#064e3b', mb: 0.4 }}>{si.name}</Typography>
          {si.description && <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.8 }}>{si.description}</Typography>}
          {si.script && (
            <Box sx={{ p: 1, bgcolor: '#1e293b', borderRadius: 1, overflowX: 'auto' }}>
              <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#a6e22e', fontSize: '0.65rem', whiteSpace: 'pre-wrap', display: 'block' }}>
                {si.script.length > 150 ? si.script.slice(0, 150) + '...' : si.script}
              </Typography>
            </Box>
          )}
        </Paper>
      ))}
    </Box>
  );
}

// ── System Properties ─────────────────────────────────────────────────────────
function SystemPropertiesBody({ properties }) {
  const TYPE_COLOR = { string: '#3b82f6', integer: '#8b5cf6', boolean: '#10b981', choice: '#f59e0b' };
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8, px: 1.5, pb: 1.5 }}>
      {properties.map((prop, i) => {
        const tc = TYPE_COLOR[prop.type] || '#64748b';
        return (
          <Paper key={i} elevation={0} sx={{ px: 1.5, py: 1, border: '1px solid #bae6fd', borderLeft: '3px solid #0891b2', borderRadius: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.3, flexWrap: 'wrap' }}>
              <Typography variant="body2" fontWeight="bold" sx={{ fontFamily: 'monospace', color: '#0c4a6e', fontSize: '0.75rem' }}>{prop.name}</Typography>
              <Typography variant="caption" sx={{ color: '#94a3b8' }}>=</Typography>
              <Chip label={prop.value} size="small" sx={{ height: 18, fontSize: '0.65rem', fontWeight: 'bold', bgcolor: '#f0f9ff', color: '#0369a1', border: '1px solid #bae6fd' }} />
              <Chip label={prop.type || 'string'} size="small" sx={{ height: 16, fontSize: '0.6rem', bgcolor: `${tc}10`, color: tc, border: `1px solid ${tc}30` }} />
            </Box>
            {prop.description && <Typography variant="caption" color="text.secondary">{prop.description}</Typography>}
          </Paper>
        );
      })}
    </Box>
  );
}

// ── Relationships ─────────────────────────────────────────────────────────────
function RelationshipsBody({ relationships }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8, px: 1.5, pb: 1.5 }}>
      {relationships.map((rel, i) => (
        <Paper key={i} elevation={0} sx={{ px: 1.5, py: 1, border: '1px solid #fca5a5', borderLeft: '3px solid #dc2626', borderRadius: 1.5 }}>
          <Typography variant="body2" fontWeight="bold" sx={{ color: '#7f1d1d', mb: 0.5 }}>{rel.name}</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Chip label={rel.parent_table} size="small" sx={{ height: 20, fontSize: '0.68rem', fontFamily: 'monospace', bgcolor: '#fef2f2', color: '#7f1d1d', border: '1px solid #fca5a5' }} />
            <Typography sx={{ color: '#dc2626', fontWeight: 'bold', fontSize: '0.85rem' }}>→</Typography>
            <Chip label={rel.child_table} size="small" sx={{ height: 20, fontSize: '0.68rem', fontFamily: 'monospace', bgcolor: '#fef2f2', color: '#7f1d1d', border: '1px solid #fca5a5' }} />
            {rel.query_with && (
              <>
                <Typography variant="caption" color="text.secondary">via</Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#64748b' }}>{rel.query_with}</Typography>
              </>
            )}
          </Box>
        </Paper>
      ))}
    </Box>
  );
}

// ── Main BlueprintPreview ─────────────────────────────────────────────────────
export default function BlueprintPreview({ blueprint, selectedFeatures }) {
  const [expandedSections, setExpandedSections] = useState({ tables: true, workflows: true });
  const toggle = (key) => setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));

  if (!blueprint) return null;

  // Map all possible blueprint keys → section key used in SECTION_CFG
  // Handles LLM returning "acls" for access_controls
  const normalizedBlueprint = {
    ...blueprint,
    access_controls: blueprint.access_controls || blueprint.acls,
  };

  const sections = [
    { key: 'tables',            data: normalizedBlueprint.tables },
    { key: 'roles',             data: normalizedBlueprint.roles },
    { key: 'forms',             data: normalizedBlueprint.forms },
    { key: 'list_layouts',      data: normalizedBlueprint.list_layouts },
    { key: 'access_controls',   data: normalizedBlueprint.access_controls },
    { key: 'navigation',        data: normalizedBlueprint.navigation },
    { key: 'workflows',         data: normalizedBlueprint.workflows },
    { key: 'notifications',     data: normalizedBlueprint.notifications },
    { key: 'approvals',         data: normalizedBlueprint.approvals },
    { key: 'client_scripts',    data: normalizedBlueprint.client_scripts },
    { key: 'script_includes',   data: normalizedBlueprint.script_includes },
    { key: 'system_properties', data: normalizedBlueprint.system_properties },
    { key: 'relationships',     data: normalizedBlueprint.relationships },
  ].filter(s => s.data?.length > 0);

  const totalItems = sections.reduce((sum, s) => sum + s.data.length, 0);

  return (
    <Box>

      {/* Module header */}
      <Box sx={{ pl: 1.5, borderLeft: '4px solid #6366f1', mb: 2 }}>
        <Typography variant="h6" fontWeight="bold">{blueprint.module_name}</Typography>
        <Typography variant="body2" color="text.secondary">{blueprint.description}</Typography>
      </Box>

      {/* Summary chips — one per section */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
        {sections.map(s => {
          const cfg = SECTION_CFG[s.key] || { color: '#64748b', title: s.key, icon: null };
          return (
            <Chip key={s.key}
              icon={<Box sx={{ color: `${cfg.color} !important`, '& svg': { fontSize: '14px !important' } }}>{cfg.icon}</Box>}
              label={`${s.data.length} ${cfg.title}`}
              size="small"
              onClick={() => toggle(s.key)}
              sx={{ bgcolor: `${cfg.color}10`, color: cfg.color, border: `1px solid ${cfg.color}30`, fontWeight: 'bold', cursor: 'pointer', fontSize: '0.72rem', '&:hover': { bgcolor: `${cfg.color}20` } }}
            />
          );
        })}
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
        {totalItems} total items will be created in ServiceNow · Click any chip or section to expand
      </Typography>

      {/* Sections */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        {sections.map(s => {
          const isExpanded = expandedSections[s.key] || false;
          const cfg        = SECTION_CFG[s.key] || { color: '#64748b' };
          return (
            <Paper key={s.key} elevation={0} sx={{ border: `1px solid ${isExpanded ? cfg.color + '40' : '#e2e8f0'}`, borderRadius: 1.5, overflow: 'hidden', transition: 'border-color 0.15s' }}>
              <SectionHeader sectionKey={s.key} count={s.data.length} expanded={isExpanded} onToggle={() => toggle(s.key)} />
              <Collapse in={isExpanded}>
                <Divider />
                {s.key === 'tables'            && <TablesBody          tables={s.data} />}
                {s.key === 'roles'             && <RolesBody           roles={s.data} />}
                {s.key === 'forms'             && <FormsBody           forms={s.data} />}
                {s.key === 'list_layouts'      && <ListLayoutsBody     layouts={s.data} />}
                {s.key === 'access_controls'   && <AccessControlsBody  acls={s.data} />}
                {s.key === 'navigation'        && <NavigationBody      items={s.data} />}
                {s.key === 'workflows'         && <WorkflowsBody       workflows={s.data} />}
                {s.key === 'notifications'     && <NotificationsBody   notifications={s.data} />}
                {s.key === 'approvals'         && <ApprovalsBody       approvals={s.data} />}
                {s.key === 'client_scripts'    && <ClientScriptsBody   scripts={s.data} />}
                {s.key === 'script_includes'   && <ScriptIncludesBody  includes={s.data} />}
                {s.key === 'system_properties' && <SystemPropertiesBody properties={s.data} />}
                {s.key === 'relationships'     && <RelationshipsBody   relationships={s.data} />}
              </Collapse>
            </Paper>
          );
        })}
      </Box>
    </Box>
  );
}