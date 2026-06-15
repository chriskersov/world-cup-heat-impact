/**
 * FIFA 2026 Climate Analysis Dashboard
 * React component with Recharts, embedded data, dark theme
 * Usage: <ClimateAnalysisDashboard />
 * Data files in /public/data/ (fetched at mount)
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, ScatterChart, Scatter, Cell, ReferenceLine, ComposedChart,
  Area, LabelList, PieChart, Pie, RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from 'recharts';
import {
  TrendingUp, TrendingDown, Minus, Sun, Moon, Download, Search, Filter,
  BarChart3, Activity, Shield, Flag, Trophy, ChevronDown, ChevronUp, X
} from 'lucide-react';

// ============================================================
// EMBEDDED DATA (replace with fetch() for production)
// ============================================================
const DATA = {
  historical: { warm_cup_win_rate: 52.5, cool_cup_win_rate: 46.1, gap_pp: 6.4, p_permutation: 0.02, p_ttest: 0.023, cohens_d: 0.15, post1990_coefficient: 0.032, n_matches: 964, n_tournaments: 22, era_pre1990_warm: 0.010, era_pre1990_cool: -0.047, era_post1990_warm: 0.032, era_post1990_cool: 0.002 },
  // Add more embedded data or use fetch()
};

// ============================================================
// DESIGN TOKENS
// ============================================================
const COLORS = {
  bg: '#0f172a', card: '#1e293b', border: '#334155',
  warm: '#ef4444', cool: '#3b82f6', warmLight: '#fca5a5', coolLight: '#93c5fd',
  text: '#f1f5f9', textDim: '#94a3b8', textMuted: '#64748b',
  accent: '#fbbf24', green: '#22c55e', greenLight: '#86efac',
  tier1: '#ef4444', tier2: '#f97316', tier3: '#fbbf24', none: '#475569',
};

const FONTS = { heading: 'Inter, system-ui, sans-serif', body: 'Inter, system-ui, sans-serif', mono: 'JetBrains Mono, monospace' };

// ============================================================
// CUSTOM HOOK: Data Loading
// ============================================================
function useData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [historical, flagged, comparison, a1results, a2results, significance, teamClimate, teamElo] = await Promise.all([
          fetch('/data/historical_summary.json').then(r => r.json()),
          fetch('/data/flagged_matchups.json').then(r => r.json()),
          fetch('/data/approach_comparison.json').then(r => r.json()),
          fetch('/data/approach1_results.json').then(r => r.json()),
          fetch('/data/approach2_results.json').then(r => r.json()),
          fetch('/data/significance.json').then(r => r.json()).catch(() => []),
          fetch('/data/team_climate.json').then(r => r.json()),
          fetch('/data/team_elo.json').then(r => r.json()),
        ]);
        setData({ historical, flagged, comparison, a1results, a2results, significance: significance || [], teamClimate, teamElo });
      } catch (e) {
        console.error('Data load error:', e);
      }
      setLoading(false);
    }
    load();
  }, []);

  return { data, loading };
}

// ============================================================
// SUB-COMPONENTS
// ============================================================

function StatTile({ value, label, color, icon: Icon }) {
  return (
    <div style={{ background: COLORS.card, borderRadius: 12, padding: '20px 24px', border: `1px solid ${COLORS.border}`, display: 'flex', alignItems: 'center', gap: 14 }}>
      {Icon && <Icon size={28} color={color} />}
      <div>
        <div style={{ fontSize: 32, fontWeight: 800, color, fontFamily: FONTS.mono, lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: 12, color: COLORS.textDim, marginTop: 4 }}>{label}</div>
      </div>
    </div>
  );
}

function SectionHeader({ title, subtitle }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: COLORS.text, margin: 0, fontFamily: FONTS.heading, letterSpacing: '-0.02em' }}>{title}</h2>
      {subtitle && <p style={{ fontSize: 14, color: COLORS.textDim, margin: '6px 0 0' }}>{subtitle}</p>}
    </div>
  );
}

function DataTable({ columns, data, rowKey, onRowClick, highlightRow }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: `2px solid ${COLORS.border}` }}>
            {columns.map(col => (
              <th key={col.key} style={{ padding: '10px 12px', textAlign: col.align || 'left', color: COLORS.textDim, fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={rowKey ? row[rowKey] : i}
                onClick={() => onRowClick && onRowClick(row)}
                style={{
                  borderBottom: `1px solid ${COLORS.border}`,
                  background: highlightRow && highlightRow(row) ? 'rgba(239, 68, 68, 0.08)' : 'transparent',
                  cursor: onRowClick ? 'pointer' : 'default',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => { if (onRowClick) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                onMouseLeave={e => { if (onRowClick && !highlightRow?.(row)) e.currentTarget.style.background = 'transparent'; }}>
              {columns.map(col => (
                <td key={col.key} style={{ padding: '10px 12px', textAlign: col.align || 'left', color: col.color ? col.color(row) : COLORS.text, fontFamily: col.mono ? FONTS.mono : FONTS.body }}>
                  {col.render ? col.render(row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================
// TAB 1: HISTORICAL ANALYSIS
// ============================================================
function HistoricalTab({ data }) {
  if (!data) return <div style={{ color: COLORS.textDim }}>Loading...</div>;
  const h = data.historical;

  return (
    <div>
      <SectionHeader title="Historical Climate Analysis" subtitle="90 years of World Cup data: does climate origin affect match outcomes?" />

      {/* Stat Tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
        <StatTile value={`${h.warm_cup_win_rate}%`} label="Warm teams win rate in warm cups" color={COLORS.warm} icon={TrendingUp} />
        <StatTile value={`${h.cool_cup_win_rate}%`} label="Warm teams win rate in cool cups" color={COLORS.cool} icon={TrendingDown} />
        <StatTile value={`+${h.gap_pp}pp`} label="Climate advantage gap" color={COLORS.accent} icon={Activity} />
        <StatTile value={`p=${h.p_permutation}`} label="Permutation test significance" color={COLORS.green} icon={Shield} />
      </div>

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Era Comparison Chart */}
        <div style={{ background: COLORS.card, borderRadius: 12, padding: 24, border: `1px solid ${COLORS.border}` }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: COLORS.text, margin: '0 0 16px' }}>Climate Effect by Era</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={[
              { era: 'Pre-1990', 'Warm Cup': h.era_pre1990_warm * 100, 'Cool Cup': h.era_pre1990_cool * 100 },
              { era: 'Post-1990', 'Warm Cup': h.era_post1990_warm * 100, 'Cool Cup': h.era_post1990_cool * 100 },
            ]} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
              <XAxis dataKey="era" stroke={COLORS.textDim} tick={{ fill: COLORS.textDim, fontSize: 12 }} />
              <YAxis stroke={COLORS.textDim} tick={{ fill: COLORS.textDim, fontSize: 11 }} label={{ value: 'Overperformance (%)', angle: -90, position: 'insideLeft', fill: COLORS.textDim, fontSize: 11 }} />
              <Tooltip contentStyle={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, color: COLORS.text }} />
              <Bar dataKey="Warm Cup" fill={COLORS.warm} radius={[6, 6, 0, 0]} />
              <Bar dataKey="Cool Cup" fill={COLORS.cool} radius={[6, 6, 0, 0]} />
              <ReferenceLine y={0} stroke={COLORS.textMuted} />
            </BarChart>
          </ResponsiveContainer>
          <p style={{ fontSize: 12, color: COLORS.textDim, marginTop: 12 }}>Post-1990 coefficient ({h.post1990_coefficient}) used in 2026 predictive model</p>
        </div>

        {/* Statistical Tests */}
        <div style={{ background: COLORS.card, borderRadius: 12, padding: 24, border: `1px solid ${COLORS.border}` }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: COLORS.text, margin: '0 0 16px' }}>Statistical Testing Suite</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              { name: 'Match-level t-test', result: `t=2.28, p=${h.p_ttest}`, sig: true, detail: 'Warm team overperformance differs between cup types' },
              { name: 'Permutation test (10k)', result: `p=${h.p_permutation}`, sig: true, detail: 'Only 10/10,000 random shuffles produce observed difference' },
              { name: 'Bootstrap CI (95%)', result: '[0.020, 0.093]', sig: true, detail: 'Confidence interval excludes zero' },
              { name: 'Mann-Whitney U', result: 'p=0.021', sig: true, detail: 'Distributional difference confirmed (non-parametric)' },
              { name: 'Mixed-effects model', result: 'Effect survives', sig: true, detail: 'Within-tournament clustering does not inflate result' },
              { name: 'Tournament OLS', result: 'R2=0.000, n=22', sig: false, detail: 'Power problem: 22 tournaments insufficient for continuous regression' },
            ].map((test, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 8, background: 'rgba(255,255,255,0.03)' }}>
                <div style={{ width: 22, height: 22, borderRadius: '50%', background: test.sig ? 'rgba(34,197,94,0.2)' : 'rgba(100,116,139,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  {test.sig ? <span style={{ color: COLORS.green, fontSize: 14 }}>&#10003;</span> : <span style={{ color: COLORS.textMuted, fontSize: 14 }}>&#10005;</span>}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.text }}>{test.name}</div>
                  <div style={{ fontSize: 11, color: COLORS.textDim }}>{test.detail}</div>
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, color: test.sig ? COLORS.green : COLORS.textMuted, fontFamily: FONTS.mono }}>{test.result}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Key Insight */}
      <div style={{ background: COLORS.card, borderRadius: 12, padding: 24, border: `1px solid ${COLORS.border}`, borderLeft: `4px solid ${COLORS.accent}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <Shield size={20} color={COLORS.accent} />
          <h3 style={{ fontSize: 16, fontWeight: 700, color: COLORS.text, margin: 0 }}>Key Finding</h3>
        </div>
        <p style={{ fontSize: 14, color: COLORS.textDim, lineHeight: 1.6, margin: 0 }}>
          After controlling for team strength via Elo ratings, warm-climate teams outperform by <strong style={{ color: COLORS.warm }}>+2.6%</strong> per match in warm World Cups vs <strong style={{ color: COLORS.cool }}>-3.0%</strong> in cool cups.
          The effect is modest (Cohen's d = {h.cohens_d}) but statistically significant across {h.n_matches} matches spanning {h.n_tournaments} tournaments.
          The post-1990 era provides the cleanest estimate: <strong style={{ color: COLORS.accent }}>+{h.post1990_coefficient}</strong> warm-team overperformance, which we use as the climate adjustment coefficient for 2026 predictions.
        </p>
      </div>
    </div>
  );
}

// ============================================================
// TAB 2: APPROACH 1 (CLIMATE FLAGGING)
// ============================================================
function Approach1Tab({ data }) {
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('all');
  const [selectedTeam, setSelectedTeam] = useState(null);

  if (!data) return <div style={{ color: COLORS.textDim }}>Loading...</div>;
  const flagged = data.flagged || [];

  const tiers = { all: 'All Tiers', 'Tier 1 (Strong)': 'Tier 1', 'Tier 2 (Moderate)': 'Tier 2', 'Tier 3 (Weak)': 'Tier 3' };
  const filtered = flagged.filter(m => {
    if (search && !m.Warm_Team.toLowerCase().includes(search.toLowerCase()) && !m.Cool_Team.toLowerCase().includes(search.toLowerCase())) return false;
    if (tierFilter !== 'all' && m.Climate_Flag_Tier !== tierFilter) return false;
    return true;
  });

  return (
    <div>
      <SectionHeader title="Approach 1: Climate Flagging" subtitle="Post-hoc climate sensitivity flags on pure Elo Monte Carlo matchups" />

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={16} color={COLORS.textMuted} style={{ position: 'absolute', left: 12, top: 11 }} />
          <input type="text" placeholder="Search team..." value={search} onChange={e => setSearch(e.target.value)}
            style={{ width: '100%', padding: '10px 12px 10px 36px', background: COLORS.bg, border: `1px solid ${COLORS.border}`, borderRadius: 8, color: COLORS.text, fontSize: 13, outline: 'none' }} />
        </div>
        {Object.entries(tiers).map(([k, v]) => (
          <button key={k} onClick={() => setTierFilter(k)} style={{
            padding: '8px 16px', borderRadius: 8, border: `1px solid ${tierFilter === k ? k === 'all' ? COLORS.warm : COLORS.accent : COLORS.border}`,
            background: tierFilter === k ? 'rgba(239,68,68,0.15)' : COLORS.bg, color: tierFilter === k ? COLORS.warm : COLORS.textDim,
            cursor: 'pointer', fontSize: 12, fontWeight: 600, transition: 'all 0.2s',
          }}>{v}</button>
        ))}
        <span style={{ color: COLORS.textMuted, fontSize: 12, alignSelf: 'center', marginLeft: 'auto' }}>{filtered.length} matchups</span>
      </div>

      {/* Scatter Plot */}
      <div style={{ background: COLORS.card, borderRadius: 12, padding: 24, border: `1px solid ${COLORS.border}`, marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: COLORS.text, margin: '0 0 16px' }}>Matchup Heat Map: Probability x Climate Sensitivity</h3>
        <ResponsiveContainer width="100%" height={420}>
          <ScatterChart margin={{ top: 20, right: 40, left: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
            <XAxis type="number" dataKey="Prob_Pct" name="Probability" unit="%" stroke={COLORS.textDim} tick={{ fill: COLORS.textDim, fontSize: 11 }}
              label={{ value: 'Matchup Probability (%)', position: 'bottom', fill: COLORS.textDim, fontSize: 12, offset: -5 }} />
            <YAxis type="number" dataKey="Climate_Diff_Score" name="Climate Score" stroke={COLORS.textDim} tick={{ fill: COLORS.textDim, fontSize: 11 }}
              label={{ value: 'Climate Differential Score', angle: -90, position: 'insideLeft', fill: COLORS.textDim, fontSize: 12, offset: 10 }} />
            <Tooltip contentStyle={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, color: COLORS.text, fontSize: 12 }}
              formatter={(v, n) => n === 'Prob_Pct' ? `${v.toFixed(1)}%` : v.toFixed(3)} />
            <ReferenceLine x={10} stroke={COLORS.accent} strokeDasharray="6 6" strokeWidth={1} />
            <ReferenceLine y={0.25} stroke={COLORS.accent} strokeDasharray="6 6" strokeWidth={1} />
            {['Tier 1 (Strong)', 'Tier 2 (Moderate)', 'Tier 3 (Weak)'].map(tier => {
              const pts = flagged.filter(m => m.Climate_Flag_Tier === tier);
              return <Scatter key={tier} name={tier} data={pts} fill={COLORS[`tier${tier.includes('1') ? '1' : tier.includes('2') ? '2' : '3'}`]} opacity={0.7} />;
            })}
          </ScatterChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', gap: 20, justifyContent: 'center', marginTop: 12, fontSize: 11, color: COLORS.textDim }}>
          <span><span style={{ color: COLORS.tier1 }}>&#9679;</span> Tier 1 (Strong)</span>
          <span><span style={{ color: COLORS.tier2 }}>&#9679;</span> Tier 2 (Moderate)</span>
          <span><span style={{ color: COLORS.tier3 }}>&#9679;</span> Tier 3 (Weak)</span>
          <span>--- x=10% | y=0.25 thresholds</span>
        </div>
      </div>

      {/* Top Flagged Table */}
      <div style={{ background: COLORS.card, borderRadius: 12, padding: 24, border: `1px solid ${COLORS.border}`, marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: COLORS.text, margin: '0 0 16px' }}>Top Flagged Matchups</h3>
        <DataTable
          columns={[
            { key: 'idx', label: '#', render: (_, i) => i + 1, mono: true },
            { key: 'Warm_Team', label: 'Warm Team', color: () => COLORS.warm },
            { key: 'Cool_Team', label: 'Cool Team', color: () => COLORS.cool },
            { key: 'Prob_Pct', label: 'Prob %', mono: true, render: r => `${r.Prob_Pct}%` },
            { key: 'Venue_Temp_C', label: 'Venue', mono: true, render: r => `${r.Venue_Temp_C.toFixed(1)}C` },
            { key: 'Climate_Diff_Score', label: 'Diff Score', mono: true, render: r => r.Climate_Diff_Score.toFixed(3) },
            { key: 'Elo_Diff', label: 'Elo Gap', mono: true, render: r => `${r.Elo_Diff > 0 ? '+' : ''}${r.Elo_Diff}` },
            { key: 'Climate_Flag_Tier', label: 'Tier', render: r => <span style={{ color: COLORS[`tier${r.Climate_Flag_Tier.includes('1') ? '1' : r.Climate_Flag_Tier.includes('2') ? '2' : '3'}`], fontWeight: 700 }}>{r.Climate_Flag_Tier}</span> },
          ]}
          data={filtered.slice(0, 25)}
          highlightRow={r => r.Climate_Flag_Tier === 'Tier 1 (Strong)'}
        />
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        <StatTile value={flagged.filter(m => m.Climate_Flag_Tier === 'Tier 1 (Strong)').length} label="Tier 1 flags (strong)" color={COLORS.tier1} icon={Flag} />
        <StatTile value={flagged.filter(m => m.Climate_Flag_Tier === 'Tier 2 (Moderate)').length} label="Tier 2 flags (moderate)" color={COLORS.tier2} icon={Flag} />
        <StatTile value={flagged.filter(m => m.Climate_Flag_Tier !== 'None').length} label="Total climate-sensitive matchups" color={COLORS.accent} icon={Activity} />
      </div>
    </div>
  );
}

// ============================================================
// TAB 3: APPROACH 2 (CLIMATE-ADJUSTED SIMULATION)
// ============================================================
function Approach2Tab({ data }) {
  if (!data) return <div style={{ color: COLORS.textDim }}>Loading...</div>;
  const comp = data.comparison || [];
  const a2r = data.a2results || [];

  const top12 = comp.sort((a, b) => b.Elo - a.Elo).slice(0, 12);
  const stages = ['QF', 'SF', 'Final', 'Winner'];

  return (
    <div>
      <SectionHeader title="Approach 2: Climate-Adjusted Simulation" subtitle="100,000 full-tournament Monte Carlo runs with climate-adjusted goal expectations" />

      {/* Win Probability Comparison */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        <div style={{ background: COLORS.card, borderRadius: 12, padding: 24, border: `1px solid ${COLORS.border}` }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: COLORS.text, margin: '0 0 16px' }}>Win Probability Shift (Top 15 by Elo)</h3>
          <ResponsiveContainer width="100%" height={380}>
            <BarChart data={comp.sort((a,b) => b.Elo - a.Elo).slice(0,15).map(t => ({
              team: t.Team,
              A1: t.A1_Winner,
              A2: t.A2_Winner,
              delta: t.Winner_Delta,
            }))} layout="vertical" margin={{ left: 80 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
              <XAxis type="number" stroke={COLORS.textDim} tick={{ fill: COLORS.textDim, fontSize: 10 }} />
              <YAxis type="category" dataKey="team" stroke={COLORS.textDim} tick={{ fill: COLORS.textDim, fontSize: 11 }} width={80} />
              <Tooltip contentStyle={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, color: COLORS.text }} />
              <Bar dataKey="A1" name="Pure Elo" fill="#64748b" radius={[0, 4, 4, 0]} />
              <Bar dataKey="A2" name="Climate-Adjusted" fill={COLORS.warm} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={{ background: COLORS.card, borderRadius: 12, padding: 24, border: `1px solid ${COLORS.border}` }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: COLORS.text, margin: '0 0 16px' }}>Win Probability Delta (A2 - A1)</h3>
          <ResponsiveContainer width="100%" height={380}>
            <BarChart data={comp.sort((a,b) => a.Winner_Delta - b.Winner_Delta).slice(0,20).map(t => ({
              team: t.Team, delta: t.Winner_Delta, warm: t.Warm === 'WARM',
            }))} layout="vertical" margin={{ left: 80 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
              <XAxis type="number" stroke={COLORS.textDim} tick={{ fill: COLORS.textDim, fontSize: 10 }} unit="pp" />
              <YAxis type="category" dataKey="team" stroke={COLORS.textDim} tick={{ fill: COLORS.textDim, fontSize: 11 }} width={80} />
              <Tooltip contentStyle={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, color: COLORS.text }} />
              <Bar dataKey="delta" name="Delta">
                {comp.sort((a,b) => a.Winner_Delta - b.Winner_Delta).slice(0,20).map((t, i) => (
                  <Cell key={i} fill={t.Winner_Delta > 0 ? COLORS.warm : COLORS.cool} />
                ))}
              </Bar>
              <ReferenceLine x={0} stroke={COLORS.textMuted} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Stage Advancement Heatmap */}
      <div style={{ background: COLORS.card, borderRadius: 12, padding: 24, border: `1px solid ${COLORS.border}`, marginBottom: 32 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: COLORS.text, margin: '0 0 16px' }}>Stage Advancement: A1 (top) vs A2 (bottom)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          {['A1', 'A2'].map(approach => {
            const prefix = approach === 'A1' ? 'A1_' : 'A2_';
            const chartData = top12.map(t => {
              const row = { team: t.Team };
              stages.forEach(s => { row[`${s}_${approach}`] = t[`${prefix}${s}`]; });
              return row;
            });
            const title = approach === 'A1' ? 'Approach 1: Pure Elo' : 'Approach 2: Climate-Adjusted';
            return (
              <div key={approach}>
                <h4 style={{ fontSize: 13, fontWeight: 600, color: COLORS.textDim, margin: '0 0 12px' }}>{title}</h4>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                    <XAxis type="number" stroke={COLORS.textDim} tick={{ fill: COLORS.textDim, fontSize: 9 }} unit="%" />
                    <YAxis type="category" dataKey="team" stroke={COLORS.textDim} tick={{ fill: COLORS.textDim, fontSize: 10 }} width={80} />
                    <Tooltip contentStyle={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, color: COLORS.text }} />
                    {stages.map((s, i) => (
                      <Bar key={s} dataKey={`${s}_${approach}`} name={s} fill={[COLORS.coolLight, COLORS.cool, COLORS.warmLight, COLORS.warm][i]} stackId="a" />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top Teams Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div style={{ background: COLORS.card, borderRadius: 12, padding: 24, border: `1px solid ${COLORS.border}` }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: COLORS.text, margin: '0 0 12px' }}>Approach 1 Top 5</h3>
          {comp.sort((a,b) => b.A1_Winner - a.A1_Winner).slice(0,5).map((t, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${COLORS.border}` }}>
              <span style={{ color: COLORS.text, fontSize: 13, fontWeight: 600 }}>{i+1}. {t.Team}</span>
              <span style={{ color: COLORS.textDim, fontFamily: FONTS.mono, fontSize: 13 }}>{t.A1_Winner.toFixed(1)}%</span>
            </div>
          ))}
        </div>
        <div style={{ background: COLORS.card, borderRadius: 12, padding: 24, border: `1px solid ${COLORS.border}` }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: COLORS.text, margin: '0 0 12px' }}>Approach 2 Top 5</h3>
          {comp.sort((a,b) => b.A2_Winner - a.A2_Winner).slice(0,5).map((t, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${COLORS.border}` }}>
              <span style={{ color: COLORS.text, fontSize: 13, fontWeight: 600 }}>{i+1}. {t.Team}</span>
              <span style={{ color: 'rgba(239,68,68,0.8)', fontFamily: FONTS.mono, fontSize: 13 }}>{t.A2_Winner.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// MAIN DASHBOARD COMPONENT
// ============================================================
export default function ClimateAnalysisDashboard() {
  const [activeTab, setActiveTab] = useState(0);
  const [darkMode, setDarkMode] = useState(true);
  const { data, loading } = useData();

  const tabs = [
    { label: 'Historical Analysis', icon: BarChart3, component: HistoricalTab },
    { label: 'Approach 1: Flagging', icon: Flag, component: Approach1Tab },
    { label: 'Approach 2: Simulation', icon: Activity, component: Approach2Tab },
  ];

  const TabComponent = tabs[activeTab].component;

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: COLORS.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', color: COLORS.textDim, fontFamily: FONTS.body }}>
        <div style={{ textAlign: 'center' }}>
          <Activity size={48} style={{ marginBottom: 16, animation: 'spin 2s linear infinite' }} />
          <p>Loading FIFA 2026 Climate Analysis...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: COLORS.bg, fontFamily: FONTS.body, color: COLORS.text }}>
      {/* Header */}
      <header style={{ position: 'sticky', top: 0, zIndex: 50, background: 'rgba(15,23,42,0.95)', backdropFilter: 'blur(12px)', borderBottom: `1px solid ${COLORS.border}`, padding: '0 32px' }}>
        <div style={{ maxWidth: 1500, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 60 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Trophy size={24} color={COLORS.accent} />
            <h1 style={{ fontSize: 18, fontWeight: 800, color: COLORS.text, margin: 0, fontFamily: FONTS.heading, letterSpacing: '-0.02em' }}>FIFA 2026 Climate Analysis</h1>
          </div>

          <nav style={{ display: 'flex', gap: 0 }}>
            {tabs.map((tab, i) => {
              const Icon = tab.icon;
              const isActive = activeTab === i;
              return (
                <button key={i} onClick={() => setActiveTab(i)} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '18px 20px', background: 'transparent', border: 'none',
                  borderBottom: isActive ? `2px solid ${COLORS.warm}` : '2px solid transparent',
                  color: isActive ? COLORS.text : COLORS.textMuted, cursor: 'pointer',
                  fontSize: 13, fontWeight: isActive ? 700 : 500, transition: 'all 0.2s',
                }}>
                  <Icon size={16} /> {tab.label}
                </button>
              );
            })}
          </nav>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 11, color: COLORS.textMuted, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: COLORS.warm }} /> Warm
              <span style={{ width: 10, height: 10, borderRadius: 2, background: COLORS.cool }} /> Cool
            </span>
          </div>
        </div>
      </header>

      {/* Content */}
      <main style={{ maxWidth: 1500, margin: '0 auto', padding: '32px' }}>
        <TabComponent data={data} />
      </main>

      {/* Footer */}
      <footer style={{ textAlign: 'center', padding: '32px', color: COLORS.textMuted, fontSize: 11, borderTop: `1px solid ${COLORS.border}` }}>
        FIFA 2026 Climate Analysis | 100,000 Monte Carlo simulations | Koppen-Geiger climate classification | Elo ratings from 49,000 international matches
      </footer>
    </div>
  );
}
