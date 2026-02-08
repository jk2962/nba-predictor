/**
 * Navbar Component
 */
import { Link, useLocation } from 'react-router-dom';

const navItems = [
    { path: '/', label: 'Home', icon: '🏠' },
    { path: '/compare', label: 'Compare', icon: '⚖️' },
    { path: '/draft', label: 'Draft Helper', icon: '📋' },
];

export default function Navbar() {
    const location = useLocation();

    return (
        <nav style={{
            background: 'rgba(15, 15, 26, 0.95)',
            backdropFilter: 'blur(10px)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            position: 'sticky',
            top: 0,
            zIndex: 50,
        }}>
            <div className="container" style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                height: '70px',
            }}>
                {/* Logo */}
                <Link to="/" style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    textDecoration: 'none',
                }}>
                    <span style={{
                        fontSize: '1.75rem',
                    }}>🏀</span>
                    <div>
                        <h1 style={{
                            fontSize: '1.25rem',
                            fontWeight: 700,
                            background: 'linear-gradient(135deg, #6366f1, #a855f7)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            margin: 0,
                        }}>
                            NBA Predictor
                        </h1>
                        <p style={{
                            fontSize: '0.7rem',
                            color: 'var(--color-text-muted)',
                            margin: 0,
                        }}>
                            AI-Powered Performance
                        </p>
                    </div>
                </Link>

                {/* Nav Links */}
                <div style={{
                    display: 'flex',
                    gap: '0.5rem',
                }}>
                    {navItems.map(({ path, label, icon }) => {
                        const isActive = location.pathname === path;
                        return (
                            <Link
                                key={path}
                                to={path}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.6rem 1.25rem',
                                    borderRadius: '0.75rem',
                                    fontSize: '0.95rem',
                                    fontWeight: 500,
                                    color: isActive ? 'white' : 'var(--color-text-secondary)',
                                    background: isActive ? 'var(--gradient-primary)' : 'transparent',
                                    border: isActive ? 'none' : '1px solid transparent',
                                    textDecoration: 'none',
                                    transition: 'all 0.2s ease',
                                }}
                                onMouseEnter={(e) => {
                                    if (!isActive) {
                                        e.currentTarget.style.background = 'var(--color-bg-tertiary)';
                                        e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.3)';
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (!isActive) {
                                        e.currentTarget.style.background = 'transparent';
                                        e.currentTarget.style.borderColor = 'transparent';
                                    }
                                }}
                            >
                                <span>{icon}</span>
                                <span>{label}</span>
                            </Link>
                        );
                    })}
                </div>
            </div>
        </nav>
    );
}
