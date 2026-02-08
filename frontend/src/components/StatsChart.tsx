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

interface StatsChartProps {
    games: GameStats[];
    prediction?: PredictionResult;
    type?: 'line' | 'bar';
    stats?: ('points' | 'rebounds' | 'assists')[];
    height?: number;
}

const STAT_COLORS = {
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
        date: new Date(game.game_date).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
        }),
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

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (!active || !payload || !payload.length) return null;

        const data = payload[0]?.payload;
        const isPrediction = label === 'Next';

        return (
            <div
                className="card"
                style={{
                    padding: '0.75rem 1rem',
                    background: 'var(--color-bg-secondary)',
                    border: isPrediction
                        ? '1px solid var(--color-nba-orange)'
                        : '1px solid rgba(255,255,255,0.1)',
                }}
            >
                <div style={{
                    fontWeight: 600,
                    marginBottom: '0.5rem',
                    color: isPrediction ? 'var(--color-nba-orange)' : 'var(--color-text-primary)',
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
                            color: entry.color,
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
                        stroke="rgba(255,255,255,0.1)"
                        vertical={false}
                    />
                    <XAxis
                        dataKey="date"
                        tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }}
                        axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                        tickLine={false}
                    />
                    <YAxis
                        tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                        wrapperStyle={{
                            paddingTop: '1rem',
                        }}
                        formatter={(value: string) => (
                            <span style={{ color: 'var(--color-text-secondary)' }}>
                                {STAT_LABELS[value as keyof typeof STAT_LABELS]}
                            </span>
                        )}
                    />

                    {prediction && (
                        <ReferenceLine
                            x="Next"
                            stroke="var(--color-nba-orange)"
                            strokeDasharray="5 5"
                            strokeWidth={2}
                        />
                    )}

                    {stats.map((stat) =>
                        type === 'bar' ? (
                            <Bar
                                key={stat}
                                dataKey={stat}
                                fill={STAT_COLORS[stat]}
                                radius={[4, 4, 0, 0]}
                                opacity={0.8}
                            />
                        ) : (
                            <Line
                                key={stat}
                                type="monotone"
                                dataKey={stat}
                                stroke={STAT_COLORS[stat]}
                                strokeWidth={2}
                                dot={{
                                    r: 4,
                                    fill: 'var(--color-bg-primary)',
                                    stroke: STAT_COLORS[stat],
                                    strokeWidth: 2,
                                }}
                                activeDot={{
                                    r: 6,
                                    fill: STAT_COLORS[stat],
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

    return (
        <div style={{ width: '100%', height }}>
            <ResponsiveContainer>
                <BarChart
                    data={chartData}
                    margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                    <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(255,255,255,0.1)"
                        vertical={false}
                    />
                    <XAxis
                        dataKey="name"
                        tick={{ fill: 'var(--color-text-primary)', fontSize: 12 }}
                        axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                        tickLine={false}
                    />
                    <YAxis
                        tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip
                        contentStyle={{
                            background: 'var(--color-bg-secondary)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '0.5rem',
                        }}
                        labelStyle={{ color: 'var(--color-text-primary)' }}
                    />
                    <Legend />
                    <Bar dataKey="points" name="Points" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="rebounds" name="Rebounds" fill="#22c55e" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="assists" name="Assists" fill="#f97316" radius={[4, 4, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}
