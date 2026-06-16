// // BlueprintValidator.jsx
// // Reusable validation panel used by NewModuleTool and ScopedAppTool.
// // Shows test results and the "Add into ServiceNow" button.

// import React, { useState } from 'react';
// import {
//   Box, Typography, Button, Card, CardContent, Chip,
//   CircularProgress, Alert, Paper, LinearProgress, Divider
// } from '@mui/material';

// import CheckCircleIcon   from '@mui/icons-material/CheckCircle';
// import CancelIcon        from '@mui/icons-material/Cancel';
// import WarningAmberIcon  from '@mui/icons-material/WarningAmber';
// import PlayArrowIcon     from '@mui/icons-material/PlayArrow';
// import CloudUploadIcon   from '@mui/icons-material/CloudUpload';
// import ScienceIcon       from '@mui/icons-material/Science';

// const API_BASE = 'http://127.0.0.1:8000';

// // ── Status icon + colour ─────────────────────────────────────────────────────
// const STATUS_CFG = {
//   pass: { color: '#16a34a', bg: '#f0fdf4', border: '#86efac', icon: <CheckCircleIcon sx={{ fontSize: 16 }} /> },
//   warn: { color: '#d97706', bg: '#fffbeb', border: '#fcd34d', icon: <WarningAmberIcon sx={{ fontSize: 16 }} /> },
//   fail: { color: '#dc2626', bg: '#fef2f2', border: '#fca5a5', icon: <CancelIcon       sx={{ fontSize: 16 }} /> },
// };

// export default function BlueprintValidator({
//   blueprint,          // the AI-generated blueprint object
//   validateEndpoint,   // '/api/validate-module' or '/api/validate-scoped-app'
//   onConfirmed,        // called when user clicks "Add into ServiceNow"
//   buildLoading,       // bool — true while SN build is running
//   selectedFeatures,
// }) {
//   const [phase,      setPhase]      = useState('idle');
//   // idle | validating | results
//   const [validation, setValidation] = useState(null);
//   const [error,      setError]      = useState(null);
//   const [showChecks, setShowChecks] = useState(false);

//   const runValidation = async () => {
//     setPhase('validating');
//     setError(null);
//     setValidation(null);
//     try {
//       const res  = await fetch(`${API_BASE}${validateEndpoint}`, {
//         method:  'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body:    JSON.stringify({ blueprint, selected_features: selectedFeatures || null, }),
//       });
//       const data = await res.json();
//       setValidation(data);
//       setPhase('results');
//     } catch (err) {
//       setError(err.message);
//       setPhase('idle');
//     }
//   };

//   const { pass = 0, warn = 0, fail = 0 } = validation?.summary || {};
//   const canProceed = validation?.can_proceed;

//   return (
//     <Box>
//       {/* ── Header card ── */}
//       <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 2, mb: 2 }}>
//         <CardContent sx={{ p: 3 }}>
//           <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
//             <ScienceIcon sx={{ color: '#6366f1' }} />
//             <Typography variant="h6" fontWeight="bold">Pre-Deployment Validation</Typography>
//           </Box>
//           <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
//             Validates the AI blueprint before making any changes in ServiceNow.
//             Checks table names, field types, scope format, name conflicts, and more.
//             <strong> Zero writes — read-only checks only.</strong>
//           </Typography>

//           {phase === 'idle' && (
//             <Button variant="outlined" startIcon={<PlayArrowIcon />}
//               onClick={runValidation} sx={{ borderColor: '#6366f1', color: '#6366f1' }}>
//               Run Validation Tests
//             </Button>
//           )}

//           {phase === 'validating' && (
//             <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
//               <CircularProgress size={20} />
//               <Typography variant="body2" color="text.secondary">
//                 Running checks against ServiceNow...
//               </Typography>
//             </Box>
//           )}

//           {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
//         </CardContent>
//       </Card>

//       {/* ── Results ── */}
//       {phase === 'results' && validation && (
//         <Box>
//           {/* Summary bar */}
//           <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
//             {[
//               { label: 'Passed',   value: pass, color: '#16a34a', icon: <CheckCircleIcon /> },
//               { label: 'Warnings', value: warn, color: '#d97706', icon: <WarningAmberIcon /> },
//               { label: 'Failed',   value: fail, color: '#dc2626', icon: <CancelIcon /> },
//             ].map(s => (
//               <Paper key={s.label} elevation={0} sx={{
//                 border: `1px solid ${s.color}30`,
//                 borderTop: `3px solid ${s.color}`,
//                 borderRadius: 2, px: 3, py: 1.5,
//                 display: 'flex', alignItems: 'center', gap: 1.5, flex: 1,
//               }}>
//                 <Box sx={{ color: s.color }}>{s.icon}</Box>
//                 <Box>
//                   <Typography variant="h5" fontWeight="bold" sx={{ color: s.color, lineHeight: 1 }}>
//                     {s.value}
//                   </Typography>
//                   <Typography variant="caption" color="text.secondary">{s.label}</Typography>
//                 </Box>
//               </Paper>
//             ))}
//           </Box>

//           {/* Overall verdict */}
//           <Alert
//             severity={fail > 0 ? 'error' : warn > 0 ? 'warning' : 'success'}
//             sx={{ mb: 2, borderRadius: 2 }}
//           >
//             {fail > 0
//               ? `❌ ${fail} critical issue(s) found. Fix them before deploying to ServiceNow.`
//               : warn > 0
//               ? `⚠️ ${warn} warning(s) found. You can still proceed — these won't block deployment.`
//               : '✅ All checks passed. Ready to deploy to ServiceNow.'
//             }
//           </Alert>

//           {/* Check list */}
//           <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 2, mb: 2 }}>
//             <CardContent sx={{ p: 2 }}>
//               <Box
//                 onClick={() => setShowChecks(prev => !prev)}
//                 sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
//                       cursor: 'pointer', userSelect: 'none' }}
//               >
//                 <Typography variant="subtitle2" fontWeight="bold" color="text.secondary">
//                   VALIDATION RESULTS ({validation.checks.length} checks)
//                 </Typography>
//                 <Typography variant="caption" sx={{ color: '#6366f1' }}>
//                   {showChecks ? '▲ Hide' : '▼ Show'}
//                 </Typography>
//               </Box>

//               {showChecks && (
//                 <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8, mt: 1.5 }}>
//                   {validation.checks.map((c, i) => {
//                     const cfg = STATUS_CFG[c.status];
//                     return (
//                       <Paper key={i} elevation={0} sx={{
//                         px: 1.5, py: 1, borderRadius: 1.5,
//                         border: `1px solid ${cfg.border}`,
//                         bgcolor: cfg.bg,
//                         display: 'flex', alignItems: 'flex-start', gap: 1,
//                       }}>
//                         <Box sx={{ color: cfg.color, mt: 0.1, flexShrink: 0 }}>{cfg.icon}</Box>
//                         <Box sx={{ flex: 1, minWidth: 0 }}>
//                           <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
//                             <Typography variant="body2" fontWeight="bold" sx={{ color: cfg.color }}>
//                               {c.check}
//                             </Typography>
//                             <Chip label={c.status.toUpperCase()} size="small"
//                               sx={{ height: 18, fontSize: '0.65rem', fontWeight: 'bold',
//                                     bgcolor: cfg.color, color: '#fff' }} />
//                           </Box>
//                           <Typography variant="caption" color="text.secondary">{c.message}</Typography>
//                           {c.detail && (
//                             <Typography variant="caption"
//                               sx={{ display: 'block', fontFamily: 'monospace',
//                                     color: '#64748b', fontSize: '0.68rem', mt: 0.3 }}>
//                               {c.detail}
//                             </Typography>
//                           )}
//                         </Box>
//                       </Paper>
//                     );
//                   })}
//                 </Box>
//               )}
//             </CardContent>
//           </Card>

//           {/* Re-run + Add to ServiceNow buttons */}
//           <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
//             <Button variant="outlined" startIcon={<PlayArrowIcon />}
//               onClick={runValidation}
//               sx={{ borderColor: '#6366f1', color: '#6366f1' }}>
//               Re-run Tests
//             </Button>

//             <Button
//               variant="contained"
//               size="large"
//               startIcon={buildLoading
//                 ? <CircularProgress size={18} color="inherit" />
//                 : <CloudUploadIcon />}
//               onClick={onConfirmed}
//               disabled={!canProceed || buildLoading}
//               sx={{
//                 px: 4,
//                 bgcolor: canProceed ? '#16a34a' : '#94a3b8',
//                 '&:hover': { bgcolor: canProceed ? '#15803d' : '#94a3b8' },
//                 '&:disabled': { bgcolor: '#e2e8f0', color: '#94a3b8' },
//               }}
//             >
//               {buildLoading
//                 ? 'Adding to ServiceNow...'
//                 : canProceed
//                 ? 'Add into ServiceNow'
//                 : 'Fix Issues First'}
//             </Button>

//             {!canProceed && (
//               <Typography variant="caption" color="error">
//                 {fail} critical check(s) must pass before deploying
//               </Typography>
//             )}
//           </Box>
//         </Box>
//       )}
//     </Box>
//   );
// }