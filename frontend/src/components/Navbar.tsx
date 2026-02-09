/**
 * Navbar Component
 */
import { Link, useLocation } from 'react-router-dom';

const navItems = [
    { path: '/', label: 'Players' },
    { path: '/browse', label: 'Browse' },
    { path: '/compare', label: 'Compare' },
    { path: '/draft', label: 'Draft' },
];

export default function Navbar() {
    const location = useLocation();

    return (
        <nav style={{
            background: 'var(--base)',
            borderBottom: '1px solid var(--border)',
            position: 'sticky',
            top: 0,
            zIndex: 50,
        }}>
            <div className="container" style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                height: '64px',
            }}>
                {/* Logo */}
                <Link to="/" style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-md)',
                    textDecoration: 'none',
                }}>
                    <div style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--hot)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '1.125rem',
                        fontWeight: 700,
                        color: 'white',
                    }}>
                        N
                    </div>
                    <div>
                        <h1 style={{
                            fontSize: '1.125rem',
                            fontWeight: 700,
                            color: 'var(--text-primary)',
                            margin: 0,
                            letterSpacing: '-0.01em',
                        }}>
                            NBA Predictor
                        </h1>
                        <p style={{
                            fontSize: '0.6875rem',
                            color: 'var(--text-tertiary)',
                            margin: 0,
                            letterSpacing: '0.02em',
                            textTransform: 'uppercase',
                        }}>
                            2025-26 Season
                        </p>
                    </div>
                </Link>

                {/* Nav Links */}
                <div style={{
                    display: 'flex',
                    gap: 'var(--space-xs)',
                }}>
                    {navItems.map(({ path, label }) => {
                        const isActive = location.pathname === path;
                        return (
                            <Link
                                key={path}
                                to={path}
                                style={{
                                    padding: '0.5rem 1rem',
                                    borderRadius: 'var(--radius-md)',
                                    fontSize: '0.875rem',
                                    fontWeight: 500,
                                    color: isActive ? 'white' : 'var(--text-secondary)',
                                    background: isActive ? 'var(--hot)' : 'transparent',
                                    border: '1px solid transparent',
                                    textDecoration: 'none',
                                    transition: 'all 0.15s ease',
                                    letterSpacing: '0.01em',
                                }}
                                onMouseEnter={(e) => {
                                    if (!isActive) {
                                        e.currentTarget.style.background = 'var(--surface-2)';
                                        e.currentTarget.style.borderColor = 'var(--border)';
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (!isActive) {
                                        e.currentTarget.style.background = 'transparent';
                                        e.currentTarget.style.borderColor = 'transparent';
                                    }
                                }}
                            >
                                {label}
                            </Link>
                        );
                    })}
                </div>
            </div>
        </nav>
    );
}
