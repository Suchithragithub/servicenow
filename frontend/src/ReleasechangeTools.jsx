import React, { useState, useEffect } from 'react';
import {
  Box, Typography, TextField, Button, Card, CardContent, Grid, 
  Accordion, AccordionSummary, AccordionDetails, CircularProgress, 
  Alert, Paper, LinearProgress, MenuItem, Divider
} from '@mui/material';

import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import AltRouteIcon from '@mui/icons-material/AltRoute';
import PlaylistAddCheckIcon from '@mui/icons-material/PlaylistAddCheck';
import AnnouncementIcon from '@mui/icons-material/Announcement';
import PublishedWithChangesIcon from '@mui/icons-material/PublishedWithChanges';
import BlockIcon from '@mui/icons-material/Block';
import DashboardCustomizeIcon from '@mui/icons-material/DashboardCustomize';
import AssignmentLateIcon from "@mui/icons-material/AssignmentLate";
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import VerifiedIcon from '@mui/icons-material/Verified';

const API_BASE = 'http://127.0.0.1:8080';

// Compacted for chat view
const MetricCard = ({ title, count, subtitle, color, icon, loading }) => (
  <Card elevation={0} sx={{ border: '1px solid #e2e8f0', bgcolor: '#ffffff', borderRadius: 2, p: 0.5, flex: '1 1 45%', minWidth: '140px' }}>
    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
        <Typography variant="caption" color="text.secondary" fontWeight="600">{title}</Typography>
        <Box sx={{ color, bgcolor: `${color}15`, p: 0.5, borderRadius: 1, display: 'flex' }}>{icon}</Box>
      </Box>
      {loading ? (
        <CircularProgress size={20} sx={{ my: 0.5, color }} />
      ) : (
        <Typography variant="h5" fontWeight="bold">{count}</Typography>
      )}
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>{subtitle}</Typography>
    </CardContent>
  </Card>
);

const StatCard = ({ label, value, color, icon }) => (
  <Card elevation={0} sx={{ border: `1px solid ${color}40`, borderTop: `4px solid ${color}`, borderRadius: 2, flex: 1, minWidth: '150px' }}>
    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="h5" fontWeight="bold" sx={{ color, lineHeight: 1 }}>{value}</Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>{label}</Typography>
        </Box>
        <Box sx={{ color, opacity: 0.6 }}>{icon}</Box>
      </Box>
    </CardContent>
  </Card>
);

// PROPS ADDED HERE: Allow the AI agent to pass in extracted entities
export default function ReleaseChangeTool({ initialTicketNumber = '', initialTableType = 'change_request' }) {
  const [ticketNumber, setTicketNumber] = useState(initialTicketNumber);
  const [tableType, setTableType] = useState(initialTableType); 
  const [instanceUrl, setInstanceUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  const [dashboardCounts, setDashboardCounts] = useState({ upcoming: 0, pending_cab: 0, ready: 0, high_risk: 0 });
  const [loadingStats, setLoadingStats] = useState(false);

  // Trigger analysis automatically if the AI passed in a ticket number
  useEffect(() => {
    if (initialTicketNumber && instanceUrl) {
      handleCheckReadiness();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTicketNumber, instanceUrl]);

  useEffect(() => {
    const initializeInstanceConfig = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/config/instance`);
        if (response.ok) {
          const data = await response.json();
          setInstanceUrl(data.instance_url);
        } else {
          throw new Error("Failed to load instance profile");
        }
      } catch (err) {
        setError(`Config Sync Error: ${err.message}`);
      }
    };
    initializeInstanceConfig();
  }, []);

  const fetchDashboardStats = async (targetUrl) => {
    const urlToUse = targetUrl || instanceUrl;
    if (!urlToUse) return;
    
    setLoadingStats(true);
    try {
      const response = await fetch(`${API_BASE}/api/release/dashboard-stats?instance_url=${encodeURIComponent(urlToUse)}`);
      if (response.ok) {
        const data = await response.json();
        setDashboardCounts(data);
      }
    } catch (err) {
      console.error("Failed to pull live dashboard counts:", err);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    if (instanceUrl) fetchDashboardStats(instanceUrl);
  }, [instanceUrl]);

  const handleCheckReadiness = async () => {
    if (!ticketNumber || !instanceUrl) return;
    setLoading(true);
    setError(null);
    setReport(null);

    try {
      const response = await fetch(`${API_BASE}/api/release/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ change_number: ticketNumber, instance_url: instanceUrl, table_name: tableType }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Analysis execution failed');
      }

      const data = await response.json();
      setReport(data);
      fetchDashboardStats(instanceUrl);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    if (status?.toLowerCase().includes('ready') || status?.toLowerCase().includes('approved')) return '#16a34a';
    if (status?.toLowerCase().includes('review')) return '#d97706';
    return '#dc2626';
  };

  const getReferenceLabel = () => tableType === 'sys_update_set' ? "Update Set ID" : "Ticket Number";

  return (
    // Max width added to prevent blowing out the chat interface
    <Box sx={{ animation: 'fadeIn 0.5s ease-in', p: 1, maxWidth: '600px', mx: 'auto' }}>
      
      {/* ── RELEASE DASHBOARD LAYER ── */}
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle1" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <DashboardCustomizeIcon color="primary" fontSize="small" />Release Metrics
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <MetricCard title="Upcoming" count={dashboardCounts.upcoming} subtitle="This week" color="#2563eb" icon={<RocketLaunchIcon fontSize="small"/>} loading={loadingStats} />
          <MetricCard title="Pending CAB" count={dashboardCounts.pending_cab} subtitle="Requires presentation" color="#d97706" icon={<HourglassEmptyIcon fontSize="small"/>} loading={loadingStats} />
          <MetricCard title="Ready" count={dashboardCounts.ready} subtitle="Passed validation" color="#16a34a" icon={<VerifiedIcon fontSize="small"/>} loading={loadingStats} />
          <MetricCard title="High-Risk" count={dashboardCounts.high_risk} subtitle="Flagged by AI" color="#dc2626" icon={<AssignmentLateIcon fontSize="small"/>} loading={loadingStats} />
        </Box>
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* ── CONTROL BAR AREA ── */}
      <Card elevation={0} sx={{ mb: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <CardContent sx={{ p: 2 }}>
          <Grid container spacing={1.5} alignItems="center">
            <Grid item xs={12} sm={5}>
              <TextField
                fullWidth select label="Type" variant="outlined" size="small"
                value={tableType} onChange={(e) => setTableType(e.target.value)} disabled={loading}
              >
                <MenuItem value="change_request">Change Request</MenuItem>
                <MenuItem value="incident">Incident</MenuItem>
                <MenuItem value="sys_update_set">Update Set</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth label={getReferenceLabel()} variant="outlined" size="small"
                value={ticketNumber} onChange={(e) => setTicketNumber(e.target.value)} disabled={loading}
              />
            </Grid>
            <Grid item xs={12} sm={3}>
              <Button
                fullWidth variant="contained" size="small" onClick={handleCheckReadiness}
                disabled={loading || !ticketNumber || !instanceUrl}
                sx={{ height: '40px' }}
              >
                {loading ? <CircularProgress size={18} color="inherit" /> : 'Analyze'}
              </Button>
            </Grid>
          </Grid> 
          {error && <Alert severity="error" sx={{ mt: 1.5, p: 0.5 }}>{error}</Alert>}
        </CardContent>
      </Card>

      {/* ── LOADING & REPORT STATES ── */}
      {loading && (
        <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2, p: 2, textAlign: 'center' }}>
          <CircularProgress size={30} sx={{ mb: 1 }} />
          <Typography variant="body2" color="text.secondary">Compiling safety validation report...</Typography>
          <LinearProgress sx={{ maxWidth: 200, mx: 'auto', mt: 1, borderRadius: 4 }} />
        </Card>
      )}

      {report && !loading && (
        <Box>
          <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
            <StatCard label="Production Readiness" value={report.production_readiness} color={getStatusColor(report.production_readiness)} icon={<PublishedWithChangesIcon />} />
            <StatCard label="Deployment Risk" value={report.risk_score} color={report.risk_score === 'High' ? '#dc2626' : report.risk_score === 'Medium' ? '#d97706' : '#16a34a'} icon={<BlockIcon />} />
          </Box>

          <Card elevation={0} sx={{ mb: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <CardContent sx={{ p: 2 }}>
              <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                <AnnouncementIcon color="primary" fontSize="small"/> CAB SUMMARY
              </Typography>
              <Paper elevation={0} sx={{ p: 1.5, bgcolor: '#f8fafc', borderRadius: 1, border: '1px solid #e2e8f0' }}>
                <Typography variant="body2">{report.cab_summary}</Typography>
              </Paper>
            </CardContent>
          </Card>

          <Card elevation={0} sx={{ mb: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <CardContent sx={{ p: 2 }}>
              <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                <PlaylistAddCheckIcon color="error" fontSize="small"/> ISSUES & GAPS
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                {report.issues_found?.length > 0 ? (
                  report.issues_found.map((issue, idx) => (
                    <Typography key={idx} variant="body2" color="#dc2626">• {issue}</Typography>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">No immediate gaps detected.</Typography>
                )}
              </Box>
            </CardContent>
          </Card>

          <Accordion elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: '8px !important', '&:before': { display: 'none' } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="body2" fontWeight="bold" color="text.secondary">View JSON Payload</Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 1 }}>
              <Paper sx={{ p: 1, backgroundColor: '#1e1e1e', color: '#a6e22e', overflowX: 'auto', maxHeight: '200px' }}>
                <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '10px' }}>{JSON.stringify(report, null, 2)}</pre>
              </Paper>
            </AccordionDetails>
          </Accordion>
        </Box>
      )}
    </Box>
  );
}
