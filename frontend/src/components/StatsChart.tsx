/**
 * Stats Chart Component using Recharts
 */
import {
    LineChart,
    Line,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    ReferenceLine,
} from 'recharts';
import type { GameStats, PredictionResult } from '../types';
import { formatGameDate } from '../utils/dateUtils';

interface StatsChartProps {
    games: GameStats[];
    prediction?: PredictionResult;
    type?: 'line' | 'bar';
    stats?: ('points' | 'rebounds' | 'assists')[];
    height?: number;
}

// Fallback hex colors for recharts (it doesn't parse CSS vars well for some props)
const STAT_COLORS_HEX = {
    points: '#6366f1',
    rebounds: '#22c55e',
    assists: '#f97316',
};

const STAT_LABELS = {
    points: 'Points',
    rebounds: 'Rebounds',
    assists: 'Assists',
};

export default function StatsChart({
    games,
    prediction,
    type = 'line',
    stats = ['points', 'rebounds', 'assists'],
    height = 300,
}: StatsChartProps) {
    // Reverse games to show oldest first (left to right)
    const chartData = [...games].reverse().map((game) => ({
        date: formatGameDate(game.game_date, 'medium').replace(/, \d{4}$/, ''),
        opponent: game.opponent_abbreviation || game.opponent_team,
        points: game.points,
        rebounds: game.rebounds,
        assists: game.assists,
        isHome: game.is_home,
    }));

    // Add prediction point if available
    if (prediction) {
        chartData.push({
            date: 'Next',
            opponent: prediction.opponent_team || 'TBD',
            points: prediction.predicted_points,
            rebounds: prediction.predicted_rebounds,
            assists: prediction.predicted_assists,
            isHome: prediction.is_home,
        });
    }

    // Get theme-aware text color
    const getTextColor = () => {
        if (typeof document !== 'undefined') {
            const theme = document.documentElement.getAttribute('data-theme');
            return theme === 'light' ? '#1f2937' : '#f9fafb';
        }
        return '#f9fafb';
    };

    const textColor = getTextColor();
    const gridColor = typeof document !== 'undefined' &&
        document.documentElement.getAttribute('data-theme') === 'light'
        ? 'rgba(0,0,0,0.1)'
        : 'rgba(255,255,255,0.1)';

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (!active || !payload || !payload.length) return null;

        const data = payload[0]?.payload;
        const isPrediction = label === 'Next';

        return (
            <div
                className="card"
                style={{
                    padding: '0.75rem 1rem',
                    background: 'var(--surface-2)',
                    border: isPrediction
                        ? '1px solid var(--hot)'
                        : '1px solid var(--border)',
                }}
            >
                <div style={{
                    fontWeight: 600,
                    marginBottom: '0.5rem',
                    color: isPrediction ? 'var(--hot)' : 'var(--text-primary)',
                }}>
                    {isPrediction ? '🔮 Prediction' : `vs ${data?.opponent}`}
                    {data?.isHome && ' (Home)'}
                </div>
                {payload.map((entry: any, index: number) => (
                    <div
                        key={index}
                        style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: '1rem',
                            fontSize: '0.875rem',
                            color: 'var(--text-primary)',
                        }}
                    >
                        <span>{STAT_LABELS[entry.dataKey as keyof typeof STAT_LABELS]}:</span>
                        <span style={{ fontWeight: 600 }}>{entry.value}</span>
                    </div>
                ))}
            </div>
        );
    };

    const Chart = type === 'bar' ? BarChart : LineChart;

    return (
        <div style={{ width: '100%', height }}>
            <ResponsiveContainer>
                <Chart
                    data={chartData}
                    margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                    <CartesianGrid
                        strokeDasharray="3 3"
                        stroke={gridColor}
                        vertical={false}
                    />
                    <XAxis
                        dataKey="date"
                        tick={{ fill: textColor, fontSize: 12 }}
                        axisLine={{ stroke: gridColor }}
                        tickLine={false}
                    />
                    <YAxis
                        tick={{ fill: textColor, fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                        wrapperStyle={{
                            paddingTop: '1rem',
                        }}
                        formatter={(value: string) => (
                            <span style={{ color: textColor }}>
                                {STAT_LABELS[value as keyof typeof STAT_LABELS]}
                            </span>
                        )}
                    />

                    {prediction && (
                        <ReferenceLine
                            x="Next"
                            stroke="var(--hot)"
                            strokeDasharray="5 5"
                            strokeWidth={2}
                        />
                    )}

                    {stats.map((stat, index) =>
                        type === 'bar' ? (
                            <Bar
                                key={stat}
                                dataKey={stat}
                                fill={STAT_COLORS_HEX[stat]}
                                radius={[4, 4, 0, 0]}
                                opacity={1 - index * 0.2}
                            />
                        ) : (
                            <Line
                                key={stat}
                                type="monotone"
                                dataKey={stat}
                                stroke={STAT_COLORS_HEX[stat]}
                                strokeWidth={2}
                                dot={{
                                    r: 4,
                                    fill: 'var(--surface-0)',
                                    stroke: STAT_COLORS_HEX[stat],
                                    strokeWidth: 2,
                                }}
                                activeDot={{
                                    r: 6,
                                    fill: STAT_COLORS_HEX[stat],
                                }}
                            />
                        )
                    )}
                </Chart>
            </ResponsiveContainer>
        </div>
    );
}

/**
 * Prediction Comparison Chart for multiple players
 */
export function ComparisonChart({
    predictions,
    height = 350,
}: {
    predictions: PredictionResult[];
    height?: number;
}) {
    const chartData = predictions.map((pred) => ({
        name: pred.player_name?.split(' ').pop() || `Player ${pred.player_id}`,
        points: pred.predicted_points,
        rebounds: pred.predicted_rebounds,
        assists: pred.predicted_assists,
        fantasy: pred.fantasy_score,
    }));

    // Get theme-aware text color
    const getTextColor = () => {
        if (typeof document !== 'undefined') {
            const theme = document.documentElement.getAttribute('data-theme');
            return theme === 'light' ? '#1f2937' : '#f9fafb';
        }
        return '#f9fafb';
    };

    const textColor = getTextColor();
    const gridColor = typeof document !== 'undefined' &&
        document.documentElement.getAttribute('data-theme') === 'light'
        ? 'rgba(0,0,0,0.1)'
        : 'rgba(255,255,255,0.1)';

    return (
        <div style={{ width: '100%', height }}>
            <ResponsiveContainer>
                <BarChart
                    data={chartData}
                    margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                    <CartesianGrid
                        strokeDasharray="3 3"
                        stroke={gridColor}
                        vertical={false}
                    />
                    <XAxis
                        dataKey="name"
                        tick={{ fill: textColor, fontSize: 12 }}
                        axisLine={{ stroke: gridColor }}
                        tickLine={false}
                    />
                    <YAxis
                        tick={{ fill: textColor, fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip
                        contentStyle={{
                            background: 'var(--surface-2)',
                            border: '1px solid var(--border)',
                            borderRadius: '0.5rem',
                            color: textColor,
                        }}
                        labelStyle={{ color: textColor }}
                    />
                    <Legend
                        formatter={(value: string) => (
                            <span style={{ color: textColor }}>{value}</span>
                        )}
                    />
                    <Bar dataKey="points" name="Points" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="rebounds" name="Rebounds" fill="#22c55e" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="assists" name="Assists" fill="#f97316" radius={[4, 4, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

