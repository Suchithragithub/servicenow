// ATFResults.jsx
// Displays ATF test suite results after a module is built.
// Replaces the old BlueprintValidator component.
// Shows test suite link, test count, and individual test list.

import React, { useState } from 'react';
import {
  Box, Typography, Paper, Chip, Button, Card, CardContent,
  CircularProgress, Alert, Divider, Collapse
} from '@mui/material';

import CheckCircleIcon   from '@mui/icons-material/CheckCircle';
import ScienceIcon       from '@mui/icons-material/Science';
import OpenInNewIcon     from '@mui/icons-material/OpenInNew';
import StorageIcon       from '@mui/icons-material/Storage';
import GroupIcon         from '@mui/icons-material/Group';
import AccountTreeIcon   from '@mui/icons-material/AccountTree';
import EmailIcon         from '@mui/icons-material/Email';
import MenuIcon          from '@mui/icons-material/Menu';
import LockIcon          from '@mui/icons-material/Lock';
import LibraryBooksIcon  from '@mui/icons-material/LibraryBooks';
import ExpandMoreIcon    from '@mui/icons-material/ExpandMore';
import ExpandLessIcon    from '@mui/icons-material/ExpandLess';
import ErrorOutlineIcon  from '@mui/icons-material/ErrorOutlined';

const API_BASE = 'http://127.0.0.1:8000';

// ── Test type → icon + color ──────────────────────────────────────────────────
const TEST_TYPE_CFG = {
  table_crud:           { icon: <StorageIcon sx={{ fontSize: 15 }} />,      color: '#3b82f6', label: 'Table CRUD'       },
  role_exists:          { icon: <GroupIcon sx={{ fontSize: 15 }} />,         color: '#f59e0b', label: 'Role'             },
  workflow_exists:      { icon: <AccountTreeIcon sx={{ fontSize: 15 }} />,   color: '#10b981', label: 'Workflow'         },
  notification_exists:  { icon: <EmailIcon sx={{ fontSize: 15 }} />,         color: '#0ea5e9', label: 'Notification'     },
  navigation_exists:    { icon: <MenuIcon sx={{ fontSize: 15 }} />,          color: '#64748b', label: 'Navigation'       },
  acl_exists:           { icon: <LockIcon sx={{ fontSize: 15 }} />,          color: '#ef4444', label: 'Access Control'   },
  script_include_exists:{ icon: <LibraryBooksIcon sx={{ fontSize: 15 }} />,  color: '#059669', label: 'Script Include'  },
};

export default function ATFResults({ atf, moduleName, snowInstance }) {
  const [expanded, setExpanded] = useState(false);

  if (!atf) return null;

  const {
    suite_name,
    suite_sys_id,
    suite_url,
    tests_created,
    tests = [],
    errors = [],
  } = atf;

  const hasErrors  = errors.length > 0;
  const hasTests   = tests_created > 0;

  return (
    <Box>
      {/* ── Suite summary card ── */}
      <Card elevation={0} sx={{
        border: `1px solid ${hasTests ? '#86efac' : '#fca5a5'}`,
        borderLeft: `4px solid ${hasTests ? '#16a34a' : '#ef4444'}`,
        borderRadius: 2, mb: 2,
      }}>
        <CardContent sx={{ p: 2.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
            <ScienceIcon sx={{ color: hasTests ? '#16a34a' : '#ef4444' }} />
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" fontWeight="bold">
                ATF Test Suite Generated
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {suite_name}
              </Typography>
            </Box>
            <Chip
              label={`${tests_created} tests`}
              size="small"
              sx={{
                bgcolor: hasTests ? '#dcfce7' : '#fef2f2',
                color:   hasTests ? '#15803d' : '#dc2626',
                fontWeight: 'bold',
                border: `1px solid ${hasTests ? '#86efac' : '#fca5a5'}`
              }}
            />
          </Box>

          {/* Stats row */}
          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', mb: 1.5 }}>
            {[
              { label: 'Table Tests',        count: tests.filter(t => t.type === 'table_crud').length,            color: '#3b82f6' },
              { label: 'Role Tests',          count: tests.filter(t => t.type === 'role_exists').length,           color: '#f59e0b' },
              { label: 'Workflow Tests',      count: tests.filter(t => t.type === 'workflow_exists').length,       color: '#10b981' },
              { label: 'Notification Tests',  count: tests.filter(t => t.type === 'notification_exists').length,  color: '#0ea5e9' },
              { label: 'Navigation Tests',    count: tests.filter(t => t.type === 'navigation_exists').length,    color: '#64748b' },
              { label: 'ACL Tests',           count: tests.filter(t => t.type === 'acl_exists').length,           color: '#ef4444' },
            ].filter(s => s.count > 0).map(s => (
              <Paper key={s.label} elevation={0} sx={{
                px: 1.5, py: 0.8, borderRadius: 1.5, textAlign: 'center',
                border: `1px solid ${s.color}30`, borderTop: `2px solid ${s.color}`,
              }}>
                <Typography variant="h6" fontWeight="bold" sx={{ color: s.color, lineHeight: 1 }}>
                  {s.count}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                  {s.label}
                </Typography>
              </Paper>
            ))}
          </Box>

          {/* Errors */}
          {hasErrors && (
            <Alert severity="warning" sx={{ mb: 1.5, borderRadius: 1.5 }}>
              {errors.length} test(s) could not be created: {errors.join(', ')}
            </Alert>
          )}

          {/* Actions */}
          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
            {suite_url && (
              <Button
                variant="contained"
                size="small"
                startIcon={<OpenInNewIcon />}
                onClick={() => window.open(suite_url, '_blank')}
                sx={{ bgcolor: '#16a34a', '&:hover': { bgcolor: '#15803d' } }}
              >
                Open Test Suite in ServiceNow
              </Button>
            )}
            {suite_url && (
              <Button
                variant="outlined"
                size="small"
                onClick={() => window.open(
                  `${snowInstance}/nav_to.do?uri=sys_atf_test_suite_test_list.do?sysparm_query=test_suite=${suite_sys_id}`,
                  '_blank'
                )}
                sx={{ borderColor: '#16a34a', color: '#16a34a' }}
              >
                View All Tests
              </Button>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* ── Test list ── */}
      {tests.length > 0 && (
        <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 2 }}>
          <CardContent sx={{ p: 2 }}>
            <Box
              onClick={() => setExpanded(prev => !prev)}
              sx={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', cursor: 'pointer', userSelect: 'none',
              }}
            >
              <Typography variant="subtitle2" fontWeight="bold" color="text.secondary">
                GENERATED TESTS ({tests.length})
              </Typography>
              <Box sx={{ color: '#6366f1' }}>
                {expanded ? <ExpandLessIcon sx={{ fontSize: 18 }} /> : <ExpandMoreIcon sx={{ fontSize: 18 }} />}
              </Box>
            </Box>

            <Collapse in={expanded}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8, mt: 1.5 }}>
                {tests.map((test, i) => {
                  const typeCfg = TEST_TYPE_CFG[test.type] || { icon: null, color: '#64748b', label: test.type };
                  return (
                    <Paper key={i} elevation={0} sx={{
                      px: 1.5, py: 1,
                      border: `1px solid ${typeCfg.color}25`,
                      borderLeft: `3px solid ${typeCfg.color}`,
                      borderRadius: 1.5,
                      display: 'flex', alignItems: 'center', gap: 1.5,
                    }}>
                      <Box sx={{ color: typeCfg.color, flexShrink: 0 }}>{typeCfg.icon}</Box>
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="body2" fontWeight="medium" noWrap>
                          {test.name}
                        </Typography>
                      </Box>
                      <Chip label={typeCfg.label} size="small"
                        sx={{ height: 18, fontSize: '0.62rem',
                              bgcolor: `${typeCfg.color}10`, color: typeCfg.color,
                              border: `1px solid ${typeCfg.color}30` }} />
                      {test.sys_id && snowInstance && (
                        <Button size="small" variant="text"
                          onClick={() => window.open(
                            `${snowInstance}/nav_to.do?uri=sys_atf_test.do?sys_id=${test.sys_id}`,
                            '_blank'
                          )}
                          sx={{ minWidth: 0, p: 0.5, color: '#94a3b8' }}>
                          <OpenInNewIcon sx={{ fontSize: 14 }} />
                        </Button>
                      )}
                    </Paper>
                  );
                })}
              </Box>
            </Collapse>
          </CardContent>
        </Card>
      )}

      {/* ── Instructions ── */}
      <Paper elevation={0} sx={{
        mt: 2, p: 2, bgcolor: '#f0f9ff',
        border: '1px solid #bae6fd', borderRadius: 2,
      }}>
        <Typography variant="caption" fontWeight="bold" color="#0369a1"
          sx={{ display: 'block', mb: 0.5 }}>
          HOW TO RUN THESE TESTS IN SERVICENOW
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.6 }}>
          1. Click "Open Test Suite in ServiceNow" above<br />
          2. Inside the test suite, click <strong>Run Test Suite</strong><br />
          3. ServiceNow will execute all tests and show Pass / Fail results<br />
          4. Each test verifies a specific component was created correctly
        </Typography>
      </Paper>
    </Box>
  );
}