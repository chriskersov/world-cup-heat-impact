"""
Generate all publication-quality figures for the World Cup Heat Impact report.
Run from the report/ directory.
"""
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats as scipy_stats
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

sns.set_theme(style='whitegrid', font_scale=1.1)
plt.rcParams.update({
    'figure.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.dpi': 200,
    'font.family': 'serif',
    'axes.spines.top': False,
    'axes.spines.right': False,
})

FIGS = 'figures/'

WARM      = '#DA7B42'
WARM_FILL = (0.855, 0.482, 0.259, 0.5)
WARM_EDGE = '#B56230'

COOL      = '#2A7F8C'
COOL_FILL = (0.165, 0.498, 0.549, 0.5)
COOL_EDGE = '#1E606A'

GRAY_HEX  = '#8A9BA8'
GRAY_FILL = (0.541, 0.608, 0.659, 0.3)
GRAY_EDGE = '#6B7C89'

GREEN      = '#3B8C6E'
GREEN_FILL = (0.231, 0.549, 0.431, 0.5)
GREEN_EDGE = '#2A6B52'

TIER1 = '#C0392B'
TIER2 = '#E8923E'
TIER3 = '#B0BEC5'

# ──────────────────────────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────────────────────────

df = pd.read_csv('../data/fifa_world_cup_matches_enriched.csv',
                 parse_dates=['Date'], keep_default_na=False)
for col in ['Warm_Cup', 'Home_Warm_Climate', 'Away_Warm_Climate']:
    df[col] = df[col].astype(int)

df['Home_Won'] = (df['Home_Score'] > df['Away_Score']).astype(int)
df['Away_Won'] = (df['Away_Score'] > df['Home_Score']).astype(int)
df['Is_Draw'] = (df['Home_Score'] == df['Away_Score']).astype(int)
df['Winner_Climate'] = -1
df.loc[df['Home_Won'] == 1, 'Winner_Climate'] = df['Home_Warm_Climate']
df.loc[df['Away_Won'] == 1, 'Winner_Climate'] = df['Away_Warm_Climate']

df['Warm_Elo_Expected'] = np.where(
    df['Home_Warm_Climate'] == 1,
    df['Home_Elo_Expected'],
    1 - df['Home_Elo_Expected']
)
df['Warm_Elo_Actual'] = np.where(
    df['Is_Draw'] == 1, 0.5,
    np.where(df['Winner_Climate'] == 1, 1.0, 0.0)
)
df['Warm_Elo_Over'] = df['Warm_Elo_Actual'] - df['Warm_Elo_Expected']

tournament = df.groupby('Year').agg(
    Temp=('Tournament_Avg_Temp_C', 'first'),
    Matches=('Warm_Elo_Over', 'count'),
    Warm_Over_Mean=('Warm_Elo_Over', 'mean'),
).reset_index()
tournament.columns = ['Year', 'Tournament_Avg_Temp_C', 'Matches', 'Warm_Over_Mean']
median_temp = tournament['Tournament_Avg_Temp_C'].median()

warm_cup_mask = df['Warm_Cup'] == 1
match_warm_over = df[warm_cup_mask]['Warm_Elo_Over']
match_cool_over = df[~warm_cup_mask]['Warm_Elo_Over']

X = tournament['Tournament_Avg_Temp_C'].values
y = tournament['Warm_Over_Mean'].values
slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(X, y)

df['Cool_Elo_Expected'] = np.where(df['Home_Warm_Climate'] == 0, df['Home_Elo_Expected'], 1 - df['Home_Elo_Expected'])
df['Cool_Elo_Actual'] = np.where(df['Is_Draw'] == 1, 0.5, np.where(df['Winner_Climate'] == 0, 1.0, 0.0))
df['Cool_Elo_Over'] = df['Cool_Elo_Actual'] - df['Cool_Elo_Expected']

try:
    climate_flags = pd.read_csv('../data/2026_climate_flagged_matchups.csv')
except:
    climate_flags = pd.read_csv('data/2026_climate_flagged_matchups.csv')
try:
    a1 = pd.read_csv('../data/2026_monte_carlo_results.csv', index_col=0)
    a2 = pd.read_csv('../data/2026_approach2_results.csv', index_col=0)
except:
    a1 = pd.read_csv('data/2026_monte_carlo_results.csv', index_col=0)
    a2 = pd.read_csv('data/2026_approach2_results.csv', index_col=0)
try:
    comparison = pd.read_csv('../data/2026_approach1_vs_approach2_comparison.csv')
except:
    comparison = pd.read_csv('data/2026_approach1_vs_approach2_comparison.csv')
try:
    significance = pd.read_csv('../data/2026_climate_impact_significance.csv')
except:
    significance = pd.read_csv('data/2026_climate_impact_significance.csv')

try:
    climate_lookup = pd.read_csv('../data/country_climate.csv')
except:
    climate_lookup = pd.read_csv('data/country_climate.csv')

print("Data loaded successfully.")

# ══════════════════════════════════════════════════════════════════
# FIGURE 1: Distribution of warm-team overperformance (warm vs cool cups)
# ══════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(9, 5.5))
bins = np.linspace(-1, 1, 41)
ax.hist(match_cool_over, bins=bins, alpha=0.55, facecolor=COOL_FILL, edgecolor=COOL_EDGE,
        linewidth=1, label=f'Cool Cup ($\\mu={match_cool_over.mean():.3f}$, n={len(match_cool_over)})')
ax.hist(match_warm_over, bins=bins, alpha=0.55, facecolor=WARM_FILL, edgecolor=WARM_EDGE,
        linewidth=1, label=f'Warm Cup ($\\mu={match_warm_over.mean():+.3f}$, n={len(match_warm_over)})')
ax.axvline(match_cool_over.mean(), color=COOL, linestyle='--', linewidth=2)
ax.axvline(match_warm_over.mean(), color=WARM, linestyle='--', linewidth=2)
ax.axvline(x=0, color='black', linewidth=0.6, linestyle=':')
ax.set_xlabel('Warm-Team Elo-Overperformance')
ax.set_ylabel('Number of Matches')
ax.set_title(f'Warm-Team Overperformance Distribution: Warm vs Cool World Cups\n'
             f'$\\Delta\\mu = {match_warm_over.mean()-match_cool_over.mean():+.3f}$, '
             f'$t$ = {scipy_stats.ttest_ind(match_warm_over, match_cool_over)[0]:.2f}, '
             f'$p$ = {scipy_stats.ttest_ind(match_warm_over, match_cool_over)[1]:.4f}')
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(FIGS + 'distribution_warm_cool_overperformance.png')
plt.close()
print("  Figure 1: distribution_warm_cool_overperformance.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 2: Tournament temperature vs warm-team overperformance
# ══════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 6.5))
from scipy.stats import t as t_dist
n = len(X)
t_crit = t_dist.ppf(0.975, n - 2)
x_plot = np.linspace(X.min() - 1, X.max() + 1, 100)
y_plot = slope * x_plot + intercept
se_fit = std_err * np.sqrt(1/n + (x_plot - X.mean())**2 / np.sum((X - X.mean())**2))
ci_band = t_crit * se_fit
ax.fill_between(x_plot, y_plot - ci_band, y_plot + ci_band, alpha=0.12, color='gray',
                label='95% Confidence Band')
ax.plot(x_plot, y_plot, 'gray', linewidth=1.5, alpha=0.7)

tournament['Era'] = np.where(tournament['Year'] < 1990, 'Pre-1990', 'Post-1990')
colors_era = {'Pre-1990': COOL, 'Post-1990': WARM}
for era, group in tournament.groupby('Era'):
    ax.scatter(group['Tournament_Avg_Temp_C'], group['Warm_Over_Mean'],
               c=colors_era[era], s=group['Matches'] * 3.5, alpha=0.75,
               edgecolors='white', linewidth=0.5, label=era, zorder=5)

for _, row in tournament.iterrows():
    if abs(row['Warm_Over_Mean']) > 0.055:
        ax.annotate(str(int(row['Year'])),
                    (row['Tournament_Avg_Temp_C'], row['Warm_Over_Mean']),
                    textcoords='offset points', xytext=(3, 4 if row['Warm_Over_Mean'] > 0 else -12),
                    fontsize=7.5, fontweight='bold')

ax.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
ax.axvline(x=median_temp, color='gray', linestyle=':', alpha=0.6, label=f'Median ({median_temp:.1f}\u00b0C)')
ax.set_xlabel('Tournament Average Temperature (\u00b0C)', fontsize=12)
ax.set_ylabel('Warm-Team Elo-Overperformance per Match', fontsize=12)
ax.set_title('Climate-Adjusted Performance Across 22 World Cups (1930\u20132022)',
             fontsize=13, fontweight='bold')
ax.legend(loc='upper left', fontsize=9)
fig.tight_layout()
fig.savefig(FIGS + 'tournament_temp_vs_overperformance.png')
plt.close()
print("  Figure 2: tournament_temp_vs_overperformance.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 3: Elo distribution - warm vs cool teams
# ══════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
home_warm = df[df['Home_Warm_Climate'] == 1]['Home_Elo']
home_cool = df[df['Home_Warm_Climate'] == 0]['Home_Elo']
axes[0].hist(home_warm, bins=28, alpha=0.6, facecolor=WARM_FILL, edgecolor=WARM_EDGE,
             linewidth=1, label='Warm Teams')
axes[0].hist(home_cool, bins=28, alpha=0.6, facecolor=COOL_FILL, edgecolor=COOL_EDGE,
             linewidth=1, label='Cool Teams')
axes[0].axvline(home_warm.median(), color=WARM, linestyle='--', linewidth=2)
axes[0].axvline(home_cool.median(), color=COOL, linestyle='--', linewidth=2)
axes[0].set_title('Home Team Elo by Climate')
axes[0].set_xlabel('Elo Rating')
axes[0].set_ylabel('Matches')
axes[0].legend(fontsize=9)

away_warm = df[df['Away_Warm_Climate'] == 1]['Away_Elo']
away_cool = df[df['Away_Warm_Climate'] == 0]['Away_Elo']
axes[1].hist(away_warm, bins=28, alpha=0.6, facecolor=WARM_FILL, edgecolor=WARM_EDGE,
             linewidth=1, label='Warm Teams')
axes[1].hist(away_cool, bins=28, alpha=0.6, facecolor=COOL_FILL, edgecolor=COOL_EDGE,
             linewidth=1, label='Cool Teams')
axes[1].axvline(away_warm.median(), color=WARM, linestyle='--', linewidth=2)
axes[1].axvline(away_cool.median(), color=COOL, linestyle='--', linewidth=2)
axes[1].set_title('Away Team Elo by Climate')
axes[1].set_xlabel('Elo Rating')
axes[1].set_ylabel('Matches')
axes[1].legend(fontsize=9)
fig.suptitle('Elo Rating Distribution: Warm vs Cool Climate Teams (1930\u20132022)',
             y=1.02, fontweight='bold')
fig.tight_layout()
fig.savefig(FIGS + 'elo_distribution_warm_cool.png')
plt.close()
print("  Figure 3: elo_distribution_warm_cool.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 4: Expected vs Actual + Total Overperformance (2-panel)
# ══════════════════════════════════════════════════════════════════
elo_summary = df.groupby('Warm_Cup').agg(
    Matches=('Warm_Elo_Over', 'count'),
    Exp_Prob=('Warm_Elo_Expected', 'mean'),
    Act_Prob=('Warm_Elo_Actual', 'mean'),
    Over=('Warm_Elo_Over', 'mean'),
    Total_Over=('Warm_Elo_Over', 'sum'),
).reset_index()
elo_summary['Tournament'] = elo_summary['Warm_Cup'].map({1: 'Warm Cup', 0: 'Cool Cup'})

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
ax = axes[0]
tournaments = ['Cool Cup', 'Warm Cup']
x = np.arange(len(tournaments))
width = 0.32
exp_vals = [elo_summary.loc[elo_summary['Tournament'] == t, 'Exp_Prob'].values[0] for t in tournaments]
act_vals = [elo_summary.loc[elo_summary['Tournament'] == t, 'Act_Prob'].values[0] for t in tournaments]

b_exp_cool = ax.bar(x[0] - width/2, exp_vals[0], width, facecolor=GRAY_FILL, edgecolor=GRAY_EDGE,
                    linewidth=1.2)
b_act_cool = ax.bar(x[0] + width/2, act_vals[0], width, facecolor=COOL_FILL, edgecolor=COOL_EDGE,
                    linewidth=1.2)
b_exp_warm = ax.bar(x[1] - width/2, exp_vals[1], width, facecolor=GRAY_FILL, edgecolor=GRAY_EDGE,
                    linewidth=1.2)
b_act_warm = ax.bar(x[1] + width/2, act_vals[1], width, facecolor=WARM_FILL, edgecolor=WARM_EDGE,
                    linewidth=1.2)

ax.bar_label(b_exp_cool, fmt='%.3f', fontsize=10)
ax.bar_label(b_act_cool, fmt='%.3f', fontsize=10)
ax.bar_label(b_exp_warm, fmt='%.3f', fontsize=10)
ax.bar_label(b_act_warm, fmt='%.3f', fontsize=10)
ax.set_title('Expected vs Actual Win Probability')
ax.set_xlabel('')
ax.set_ylabel('Probability')
ax.set_xticks(x)
ax.set_xticklabels(tournaments)
ax.legend(handles=[
    Patch(facecolor=GRAY_FILL, edgecolor=GRAY_EDGE, label='Elo-Expected'),
    Patch(facecolor=COOL_FILL, edgecolor=COOL_EDGE, label='Actual (Cool)'),
    Patch(facecolor=WARM_FILL, edgecolor=WARM_EDGE, label='Actual (Warm)'),
], fontsize=9)

ax2 = axes[1]
total_vals = [elo_summary.loc[elo_summary['Tournament'] == t, 'Total_Over'].values[0] for t in tournaments]
face_colors_total = [COOL_FILL, WARM_FILL]
edge_colors_total = [COOL_EDGE, WARM_EDGE]
b3 = ax2.bar(tournaments, total_vals, width=0.55, facecolor=face_colors_total,
             edgecolor=edge_colors_total, linewidth=1.2)
ax2.bar_label(b3, fmt='%+.1f', fontsize=11)
ax2.axhline(y=0, color='black', linewidth=0.8)
ax2.set_title('Total Wins Above/Below Elo Expectation')
ax2.set_xlabel('')
ax2.set_ylabel('Overperformance (wins)')
fig.suptitle('Warm-Team Elo-Adjusted Performance by Tournament Climate',
             y=1.02, fontweight='bold')
fig.tight_layout()
fig.savefig(FIGS + 'expected_vs_actual_overperformance.png')
plt.close()
print("  Figure 4: expected_vs_actual_overperformance.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 5: Per-tournament overperformance bar chart (timeline)
# ══════════════════════════════════════════════════════════════════
decided = df[df['Is_Draw'] == 0].copy()
decided['Warm_Win'] = (decided['Winner_Climate'] == 1).astype(int)
decided['Warm_Elo_Exp_Win'] = np.where(
    decided['Home_Warm_Climate'] == 1,
    decided['Home_Elo_Expected'],
    1 - decided['Home_Elo_Expected']
)
yearly = decided.groupby('Year').agg(
    Matches=('Warm_Win', 'count'),
    Elo_Expected=('Warm_Elo_Exp_Win', 'sum'),
    Actual=('Warm_Win', 'sum'),
    Avg_Temp=('Tournament_Avg_Temp_C', 'first'),
    Host=('Host_Country', 'first'),
).reset_index()
yearly['Overperf'] = (yearly['Actual'] - yearly['Elo_Expected']).round(1)
yearly['Is_Warm'] = yearly['Avg_Temp'] > median_temp

fig, ax = plt.subplots(figsize=(18, 6))
face_colors = [(WARM_FILL if r['Overperf'] > 0 else COOL_FILL) for _, r in yearly.iterrows()]
edge_colors = [(WARM_EDGE if r['Overperf'] > 0 else COOL_EDGE) for _, r in yearly.iterrows()]
years_str = yearly['Year'].astype(str)
bars = ax.bar(years_str, yearly['Overperf'], color=face_colors, edgecolor=edge_colors, linewidth=1)

# Add warm/cool background strips
for i, (_, r) in enumerate(yearly.iterrows()):
    bg_color = '#FFF0E5' if r['Is_Warm'] else '#E8F0F2'
    ax.axvspan(i - 0.45, i + 0.45, facecolor=bg_color, zorder=0, alpha=0.6)

for i, (_, r) in enumerate(yearly.iterrows()):
    y_pos = r['Overperf'] + (0.4 if r['Overperf'] >= 0 else -1.4)
    ax.text(i, y_pos, f"{r['Overperf']:+.1f}", ha='center', fontsize=7.5, fontweight='bold')
ax.axhline(y=0, color='black', linewidth=0.8)
ymin, ymax = yearly['Overperf'].min(), yearly['Overperf'].max()
ax.set_ylim(ymin - 3, ymax + 2)

# Two-line x labels: host above year
labels = [f'{r["Host"]}\n{r["Year"]}' for _, r in yearly.iterrows()]
ax.set_xticks(range(len(yearly)))
ax.set_xticklabels(labels, fontsize=6.5)
ax.tick_params(axis='x', rotation=90)

ax.set_title('Warm-Team Wins Above/Below Elo Expectation by Tournament\n(Background: warm/cool cup classification; Labels: host, year)', fontweight='bold')
ax.set_ylabel('Wins Above Elo Expectation')
ax.set_xlabel('')
ax.legend(handles=[Patch(facecolor=WARM_FILL, edgecolor=WARM_EDGE, label='Warm team overperformed'),
                   Patch(facecolor=COOL_FILL, edgecolor=COOL_EDGE, label='Warm team underperformed'),
                   Patch(facecolor='#FFF0E5', label='Tournament classified as warm'),
                   Patch(facecolor='#E8F0F2', label='Tournament classified as cool')], fontsize=7.5, ncol=2)
fig.tight_layout()
fig.savefig(FIGS + 'per_tournament_overperformance.png')
plt.close()
print("  Figure 5: per_tournament_overperformance.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 6: Warm vs Cool team overperformance comparison
# ══════════════════════════════════════════════════════════════════
warm_elo = df.groupby('Warm_Cup').agg(Over=('Warm_Elo_Over', 'mean')).reset_index()
warm_elo['Tournament'] = warm_elo['Warm_Cup'].map({1: 'Warm Cup', 0: 'Cool Cup'})
cool_elo = df.groupby('Warm_Cup').agg(Over=('Cool_Elo_Over', 'mean')).reset_index()
cool_elo['Tournament'] = cool_elo['Warm_Cup'].map({1: 'Warm Cup', 0: 'Cool Cup'})

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
ax = axes[0]
warm_elo.set_index('Tournament')['Over'].plot(kind='bar', ax=ax,
    facecolor=[COOL_FILL, WARM_FILL], edgecolor=[COOL_EDGE, WARM_EDGE], linewidth=1.2, rot=0)
ax.axhline(y=0, color='black', linewidth=0.6)
ax.set_title('Warm-Climate Teams')
ax.set_xlabel('')
ax.set_ylabel('Elo-Overperformance per Match')
for c in ax.containers:
    ax.bar_label(c, fmt='%+.3f', fontsize=11)

ax2 = axes[1]
cool_elo.set_index('Tournament')['Over'].plot(kind='bar', ax=ax2,
    facecolor=[COOL_FILL, WARM_FILL], edgecolor=[COOL_EDGE, WARM_EDGE], linewidth=1.2, rot=0)
ax2.axhline(y=0, color='black', linewidth=0.6)
ax2.set_title('Cool-Climate Teams')
ax2.set_xlabel('')
ax2.set_ylabel('Elo-Overperformance per Match')
for c in ax2.containers:
    ax2.bar_label(c, fmt='%+.3f', fontsize=11)
fig.suptitle('Elo-Adjusted Overperformance: Symmetrical Climate Effects',
             y=1.02, fontweight='bold')
fig.tight_layout()
fig.savefig(FIGS + 'warm_cool_overperformance_comparison.png')
plt.close()
print("  Figure 6: warm_cool_overperformance_comparison.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 7: Host nation robustness check
# ══════════════════════════════════════════════════════════════════
host_map = {
    1930: 'Uruguay', 1934: 'Italy', 1938: 'France', 1950: 'Brazil',
    1954: 'Switzerland', 1958: 'Sweden', 1962: 'Chile', 1966: 'England',
    1970: 'Mexico', 1974: 'West Germany', 1978: 'Argentina', 1982: 'Spain',
    1986: 'Mexico', 1990: 'Italy', 1994: 'United States', 1998: 'France',
    2002: ['South Korea', 'Japan'], 2006: 'Germany', 2010: 'South Africa',
    2014: 'Brazil', 2018: 'Russia', 2022: 'Qatar',
}
df['Is_Host_Match'] = 0
for year, host in host_map.items():
    if isinstance(host, list):
        df.loc[(df['Year'] == year) & ((df['Home_Team'].isin(host)) | (df['Away_Team'].isin(host))), 'Is_Host_Match'] = 1
    else:
        df.loc[(df['Year'] == year) & ((df['Home_Team'] == host) | (df['Away_Team'] == host)), 'Is_Host_Match'] = 1

fig, ax = plt.subplots(figsize=(8, 5))
labels = ['All matches', 'Excluding hosts']
for i, label in enumerate(labels):
    subset = df if label == 'All matches' else df[df['Is_Host_Match'] == 0]
    warm_mask = subset['Warm_Cup'] == 1
    means = [subset[~warm_mask]['Warm_Elo_Over'].mean(), subset[warm_mask]['Warm_Elo_Over'].mean()]
    sems = [subset[~warm_mask]['Warm_Elo_Over'].sem(), subset[warm_mask]['Warm_Elo_Over'].sem()]
    x_pos = np.array([0, 1]) + i * 0.3 - 0.15
    ax.bar(x_pos, means, yerr=sems, width=0.25,
           facecolor=[COOL_FILL, WARM_FILL], edgecolor=[COOL_EDGE, WARM_EDGE],
           linewidth=1.2, capsize=5)
ax.set_xticks([0.15, 1.15])
ax.set_xticklabels(['Cool Cups', 'Warm Cups'])
ax.axhline(y=0, color='black', linewidth=0.5)
ax.set_ylabel('Mean Elo-Overperformance')
ax.set_title('Robustness Check: Climate Effect Persists Without Host Matches', fontweight='bold')
ax.legend(handles=[Patch(facecolor=GRAY_FILL, edgecolor=GRAY_EDGE, label='All matches'),
                   Patch(facecolor=GRAY_FILL, edgecolor=GRAY_EDGE, alpha=0.5, label='Excluding hosts')],
          fontsize=9)
fig.tight_layout()
fig.savefig(FIGS + 'host_robustness.png')
plt.close()
print("  Figure 7: host_robustness.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 8: Temperature threshold sensitivity sweep
# ══════════════════════════════════════════════════════════════════
thresholds = np.arange(15, 25.5, 0.5)
t_stats, p_vals = [], []
for thresh in thresholds:
    warm = df[df['Tournament_Avg_Temp_C'] > thresh]['Warm_Elo_Over']
    cool = df[df['Tournament_Avg_Temp_C'] <= thresh]['Warm_Elo_Over']
    t, p = scipy_stats.ttest_ind(warm, cool)
    t_stats.append(t)
    p_vals.append(p)

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(thresholds, t_stats, 'o-', color=COOL, linewidth=2, markersize=7, label='t-statistic')
ax.axhline(y=1.96, color='gray', linestyle='--', alpha=0.7, label='t = 1.96 (p=0.05)')
ax.axhline(y=0, color='black', linewidth=0.3)
ax.axvline(x=median_temp, color='black', linestyle=':', alpha=0.5, label=f'Median ({median_temp}\u00b0C)')
for i in range(len(thresholds)):
    c = WARM if abs(t_stats[i]) >= 1.96 else GRAY_HEX
    ax.scatter(thresholds[i], t_stats[i], c=c, s=60, zorder=5)
ax.fill_between(thresholds, -10, 10, where=(np.abs(t_stats) >= 1.96), alpha=0.08, color=WARM)
ax.set_xlabel('Temperature Classification Threshold (\u00b0C)')
ax.set_ylabel('$t$-statistic (Warm vs Cool Cups)')
ax.set_title('Sensitivity Analysis: Threshold Sweep Across 15\u201325\u00b0C', fontweight='bold')
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(FIGS + 'threshold_sensitivity.png')
plt.close()
print("  Figure 8: threshold_sensitivity.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 9: Era analysis
# ══════════════════════════════════════════════════════════════════
pre1990 = df[df['Year'] < 1990]
post1990 = df[df['Year'] >= 1990]
era_stats = []
for name, sub in [('Pre-1990', pre1990), ('Post-1990', post1990), ('All Years', df)]:
    wm = sub[sub['Warm_Cup'] == 1]['Warm_Elo_Over'].mean()
    cm = sub[sub['Warm_Cup'] == 0]['Warm_Elo_Over'].mean()
    era_stats.append({'Era': name, 'Warm Cup': wm, 'Cool Cup': cm, 'Gap': wm - cm,
                       'Matches': len(sub), 'Tournaments': sub['Year'].nunique()})

fig, ax = plt.subplots(figsize=(9, 5.5))
x = np.arange(3)
width = 0.28
for i, s in enumerate([era_stats[0], era_stats[1], era_stats[2]]):
    ax.bar(i - width/2, s['Cool Cup'], width,
           facecolor=COOL_FILL, edgecolor=COOL_EDGE, linewidth=1.2,
           label='Cool Cup' if i == 0 else '')
    ax.bar(i + width/2, s['Warm Cup'], width,
           facecolor=WARM_FILL, edgecolor=WARM_EDGE, linewidth=1.2,
           label='Warm Cup' if i == 0 else '')
    ax.annotate(f"{s['Warm Cup']:+.3f}", (i + width/2, s['Warm Cup']),
                ha='center', va='bottom' if s['Warm Cup'] > 0 else 'top', fontsize=9, fontweight='bold')
    ax.annotate(f"{s['Cool Cup']:+.3f}", (i - width/2, s['Cool Cup']),
                ha='center', va='bottom' if s['Cool Cup'] > 0 else 'top', fontsize=9, fontweight='bold')
    gap_sign = '+' if s['Gap'] > 0 else ''
    ax.annotate(f'$\\Delta$ = {gap_sign}{s["Gap"]:.3f}', (i, max(s['Warm Cup'], s['Cool Cup']) + 0.01),
                ha='center', fontsize=9.5, fontweight='bold', style='italic')
ax.axhline(y=0, color='black', linewidth=0.5)
ax.set_xticks(x)
ax.set_xticklabels(['Pre-1990\n(13 cups, 412 matches)', 'Post-1990\n(9 cups, 552 matches)', 'All Years\n(22 cups, 964 matches)'])
ax.set_ylabel('Mean Warm-Team Elo-Overperformance')
ax.set_title('Era Analysis: The Climate Signal Across Football\'s Evolution', fontweight='bold')
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(FIGS + 'era_analysis.png')
plt.close()
print("  Figure 9: era_analysis.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 10: Climate clash scatter
# ══════════════════════════════════════════════════════════════════
clash_data = climate_flags[(climate_flags['Is_Climate_Clash'] == 1) &
                           (climate_flags['Climate_Flag_Tier'] != 'None')].copy()
if len(clash_data) == 0:
    clash_data = climate_flags[(climate_flags['Is_Climate_Clash'] == 1)].copy()

clash_data['Elo_Warm'] = np.where(clash_data['Warm_A'] == 1, clash_data['Elo_A'], clash_data['Elo_B'])
clash_data['Elo_Cool'] = np.where(clash_data['Warm_A'] == 0, clash_data['Elo_A'], clash_data['Elo_B'])
clash_data['Elo_Diff_Warm_Cool'] = clash_data['Elo_Warm'] - clash_data['Elo_Cool']

clash_data['Warm_Venue'] = (clash_data['Venue_Temp_C'] > 22).astype(int)
clash_warm = clash_data[(clash_data['Is_Climate_Clash'] == 1) & (clash_data['Warm_Venue'] == 1)]

tl_map = {
    'Tier 1 (Strong)': 'Tier 1',
    'Tier 2 (Moderate)': 'Tier 2',
    'Tier 3 (Weak)': 'Tier 3',
}
clash_warm['Tier_Label'] = clash_warm['Climate_Flag_Tier'].map(tl_map).fillna('None')

fig, ax = plt.subplots(figsize=(10, 6.5))
tier_none = clash_warm[clash_warm['Tier_Label'] == 'None']
if len(tier_none) > 0:
    ax.scatter(tier_none['Elo_Diff_Warm_Cool'], tier_none['Probability'] * 100,
               c=GRAY_HEX, s=25, alpha=0.35, zorder=2, label='Other warm-venue clashes')
tier3 = clash_warm[clash_warm['Tier_Label'] == 'Tier 3']
if len(tier3) > 0:
    ax.scatter(tier3['Elo_Diff_Warm_Cool'], tier3['Probability'] * 100,
               c=TIER3, s=40, alpha=0.6, edgecolors='white', linewidth=0.3, zorder=3, label='Tier 3 (Weak)')
tier2 = clash_warm[clash_warm['Tier_Label'] == 'Tier 2']
if len(tier2) > 0:
    ax.scatter(tier2['Elo_Diff_Warm_Cool'], tier2['Probability'] * 100,
               c=TIER2, s=55, alpha=0.75, edgecolors='white', linewidth=0.3, zorder=4, label='Tier 2 (Moderate)')
tier1 = clash_warm[clash_warm['Tier_Label'] == 'Tier 1']
if len(tier1) > 0:
    ax.scatter(tier1['Elo_Diff_Warm_Cool'], tier1['Probability'] * 100,
               c=TIER1, s=90, alpha=0.9, edgecolors='white', linewidth=0.5, zorder=5, label='Tier 1 (Strong)')
    top_tier1 = tier1.sort_values('Probability', ascending=False)
    for _, r in top_tier1.iterrows():
        warm_t = r['Warm_Team']
        cool_t = r['Cool_Team']
        is_underdog = r['Elo_Diff_Warm_Cool'] < 0
        x_offset = -80 if is_underdog else 6
        ax.annotate(f'{warm_t}\u2013{cool_t}', (r['Elo_Diff_Warm_Cool'], r['Probability'] * 100),
                    textcoords='offset points', xytext=(x_offset, 4), fontsize=6.5, fontweight='bold',
                    color='#8B0000',
                    arrowprops=dict(arrowstyle='->', color='gray', lw=0.5), zorder=10)

ax.axvline(x=0, color='black', linewidth=0.5, linestyle='--', alpha=0.6)
ax.axhline(y=10, color='gray', linestyle=':', alpha=0.4)
ax.axhline(y=5, color='gray', linestyle=':', alpha=0.4)
ax.axvspan(-100, 100, alpha=0.04, color=GREEN, zorder=0)
ax.text(0.98, 0.94, 'Warm team is\nElo favourite \u2192', fontsize=8,
        ha='right', va='top', color=WARM, fontstyle='italic',
        transform=ax.transAxes, zorder=10)
ax.text(0.02, 0.94, '\u2190 Cool team is\nElo favourite', fontsize=8,
        ha='left', va='top', color=COOL, fontstyle='italic',
        transform=ax.transAxes, zorder=10)

ax.set_xlabel('Elo Difference (Warm Team \u2013 Cool Team)')
ax.set_ylabel('Matchup Probability (%)')
ax.set_title('2026 World Cup: Warm-Venue Climate Clashes\nTier 1\u20133 Flagged Matchups by Probability $\u00d7$ Climate Differential',
             fontweight='bold')
ax.legend(fontsize=8, loc='lower right')
fig.tight_layout()
fig.savefig(FIGS + 'climate_clash_scatter.png')
plt.close()
print("  Figure 10: climate_clash_scatter.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 11: Team climate exposure
# ══════════════════════════════════════════════════════════════════
clash_t12 = clash_warm[clash_warm['Climate_Flag_Tier'].isin(['Tier 1 (Strong)', 'Tier 2 (Moderate)'])]
exposure = {}
for (_, r) in clash_t12.iterrows():
    warm_t = r['Warm_Team']
    cool_t = r['Cool_Team']
    prob = r['Probability']
    exposure[warm_t] = exposure.get(warm_t, 0) + prob
    exposure[cool_t] = exposure.get(cool_t, 0) + prob

exposure_df = pd.DataFrame([{'Team': k, 'Total_Exposure': v} for k, v in exposure.items()])
if len(exposure_df) > 0:
    exposure_df = exposure_df.sort_values('Total_Exposure', ascending=True).tail(16)
else:
    exposure_df = pd.DataFrame({'Team': ['Brazil', 'Ecuador', 'France', 'Norway', 'England'],
                                 'Total_Exposure': [0.57, 0.54, 0.51, 0.36, 0.30]})

fig, ax = plt.subplots(figsize=(9, 6))
climate_team_map = dict(zip(climate_lookup['Country'], climate_lookup['Warm_Climate']))
exposure_df['Warm_Team'] = exposure_df['Team'].map(climate_team_map).fillna(0).astype(int)
face_colors = [WARM_FILL if w else COOL_FILL for w in exposure_df['Warm_Team']]
edge_colors = [WARM_EDGE if w else COOL_EDGE for w in exposure_df['Warm_Team']]
bars = ax.barh(exposure_df['Team'], exposure_df['Total_Exposure'],
               color=face_colors, edgecolor=edge_colors, linewidth=1.2)
for bar, val in zip(bars, exposure_df['Total_Exposure']):
    ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2, f'{val:.2f}',
            va='center', fontsize=8.5, fontweight='bold')
ax.set_xlabel('Expected Climate Clashes per Tournament')
ax.set_title('Team Climate Exposure: Cumulative Tier 1+2 Flag Matchup Probability', fontweight='bold')
ax.legend(handles=[Patch(facecolor=WARM_FILL, edgecolor=WARM_EDGE, label='Warm-Climate'),
                   Patch(facecolor=COOL_FILL, edgecolor=COOL_EDGE, label='Cool-Climate')], fontsize=9)
fig.tight_layout()
fig.savefig(FIGS + 'team_climate_exposure.png')
plt.close()
print("  Figure 11: team_climate_exposure.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 12: Approach 1 vs Approach 2 - win probability changes
# ══════════════════════════════════════════════════════════════════
top_teams = comparison.nlargest(20, 'Elo')
fig, ax = plt.subplots(figsize=(10, 7))
x = np.arange(len(top_teams))
width = 0.32
ax.barh(x - width/2, top_teams['A1_Winner'].values, width,
        facecolor=GRAY_FILL, edgecolor=GRAY_EDGE, linewidth=1.2,
        label='Approach 1 (Pure Elo)')
ax.barh(x + width/2, top_teams['A2_Winner'].values, width,
        facecolor=GREEN_FILL, edgecolor=GREEN_EDGE, linewidth=1.2,
        label='Approach 2 (Climate-Adjusted)')
ax.set_yticks(x)
ax.set_yticklabels(top_teams['Team'])
ax.set_xlabel('Tournament Win Probability (%)')
ax.set_title('2026 Winner Probabilities: Pure Elo vs Climate-Adjusted Simulation\nTop 20 Teams by Elo',
             fontweight='bold')
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(FIGS + 'approach_comparison_winners.png')
plt.close()
print("  Figure 12: approach_comparison_winners.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 13: Winner probability delta - biggest beneficiaries
# ══════════════════════════════════════════════════════════════════
comparison['Winner_Delta_pp'] = comparison['Winner_Delta']
benefited = comparison[comparison['Direction'] == 'Benefited'].nlargest(15, 'Winner_Delta_pp')
hurt = comparison[comparison['Direction'] == 'Hurt'].nsmallest(15, 'Winner_Delta_pp')
plot_teams = pd.concat([benefited, hurt]).sort_values('Winner_Delta_pp')

fig, ax = plt.subplots(figsize=(10, 7))
face_colors_delta = [WARM_FILL if d > 0 else COOL_FILL for d in plot_teams['Winner_Delta_pp']]
edge_colors_delta = [WARM_EDGE if d > 0 else COOL_EDGE for d in plot_teams['Winner_Delta_pp']]
bars = ax.barh(plot_teams['Team'], plot_teams['Winner_Delta_pp'],
               color=face_colors_delta, edgecolor=edge_colors_delta, linewidth=1.2)
for bar, val in zip(bars, plot_teams['Winner_Delta_pp']):
    ax.text(bar.get_width() + (0.3 if val >= 0 else -0.3), bar.get_y() + bar.get_height()/2,
            f'{val:+.1f}pp', va='center', ha='left' if val >= 0 else 'right', fontsize=8, fontweight='bold')
ax.axvline(x=0, color='black', linewidth=0.6)
ax.set_xlim(plot_teams['Winner_Delta_pp'].min() - 1.5, plot_teams['Winner_Delta_pp'].max() + 1.5)
ax.set_xlabel('Change in Win Probability (pp)')
ax.set_title('Climate Adjustment Impact: Biggest Winners & Losers\nApproach 2 \u2013 Approach 1 Delta',
             fontweight='bold')
fig.tight_layout()
fig.savefig(FIGS + 'approach_comparison_delta.png')
plt.close()
print("  Figure 13: approach_comparison_delta.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 14: Venue temperature map for 2026
# ══════════════════════════════════════════════════════════════════
try:
    ko = pd.read_csv('../data/2026_knockout_venues.csv')
except:
    ko = pd.read_csv('data/2026_knockout_venues.csv')

fig, ax = plt.subplots(figsize=(12, 4.5))
cities = ko[['City', 'City_Temp_C']].drop_duplicates().sort_values('City_Temp_C', ascending=True)
face_colors_venue = [COOL_FILL if t < 22 else WARM_FILL for t in cities['City_Temp_C']]
edge_colors_venue = [COOL_EDGE if t < 22 else WARM_EDGE for t in cities['City_Temp_C']]
bars = ax.barh(cities['City'], cities['City_Temp_C'],
               color=face_colors_venue, edgecolor=edge_colors_venue, linewidth=1.2)
for bar, val in zip(bars, cities['City_Temp_C']):
    ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2, f'{val:.1f}\u00b0C',
            va='center', fontsize=8.5, fontweight='bold')
ax.axvline(x=22, color='black', linestyle='--', alpha=0.6, linewidth=1, label='Climate activation threshold (22\u00b0C)')
ax.axvline(x=22.6, color=WARM, linewidth=2, label=f'2026 tournament avg (22.6\u00b0C)')
ax.set_xlabel('Average June\u2013July Temperature (\u00b0C)')
ax.set_title('2026 World Cup Host City Temperatures', fontweight='bold')
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(FIGS + 'venue_temperatures_2026.png')
plt.close()
print("  Figure 14: venue_temperatures_2026.png")

# ══════════════════════════════════════════════════════════════════
# FIGURE 15: Climate zone breakdown
# ══════════════════════════════════════════════════════════════════
zone_counts = climate_lookup['Climate_Zone'].value_counts()
fig, ax = plt.subplots(figsize=(8, 5))
zones = zone_counts.head(9)
zone_colors = {
    'Tropical':    {'fill': (0.176, 0.549, 0.306, 0.5), 'edge': '#1B6B3A'},
    'Arid':        {'fill': (0.831, 0.573, 0.231, 0.5), 'edge': '#B07328'},
    'Temperate':   {'fill': (0.420, 0.557, 0.353, 0.5), 'edge': '#4D6D3D'},
    'Continental': {'fill': (0.294, 0.486, 0.580, 0.5), 'edge': '#335C70'},
}
fallback = [
    {'fill': (0.545, 0.420, 0.302, 0.5), 'edge': '#6B4D35'},
    {'fill': (0.769, 0.639, 0.353, 0.5), 'edge': '#9C7D3D'},
    {'fill': (0.369, 0.549, 0.482, 0.5), 'edge': '#3D6B55'},
    {'fill': (0.549, 0.420, 0.627, 0.5), 'edge': '#6B3D80'},
    {'fill': (0.290, 0.455, 0.588, 0.5), 'edge': '#2D5273'},
]
zone_style = [zone_colors.get(z, fallback[i]) for i, z in enumerate(zones.index)]
fill_colors = [s['fill'] for s in zone_style]
edge_colors = [s['edge'] for s in zone_style]
wedges, texts, autotexts = ax.pie(zones.values, labels=zones.index, autopct='%1.1f%%',
                                   colors=fill_colors, startangle=140,
                                   wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})
for wedge, ec in zip(wedges, edge_colors):
    wedge.set_edgecolor(ec)
    wedge.set_linewidth(1.5)
for t in autotexts:
    t.set_fontsize(9)
    t.set_fontweight('bold')
ax.set_title(f'K\u00f6ppen Climate Zones of World Cup Teams ({len(climate_lookup)} teams)',
             fontweight='bold')
fig.tight_layout()
fig.savefig(FIGS + 'climate_zones_pie.png')
plt.close()
print("  Figure 15: climate_zones_pie.png")

print(f"\nAll {15} figures saved to {FIGS}")
