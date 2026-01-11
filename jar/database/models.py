"""
Oracle database setup with sample schema for application monitoring.
Uses SQLite to simulate Oracle database.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import random
import os

Base = declarative_base()

# Database path configuration
def get_db_path():
    """Get the database path from environment or default."""
    return os.getenv('DATABASE_PATH', 'oracle_pilot.db')


class Application(Base):
    """Applications being monitored."""
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    environment = Column(String(50))
    status = Column(String(20))
    owner = Column(String(100))
    description = Column(Text)


class PerformanceThreshold(Base):
    """Performance thresholds for monitored applications."""
    __tablename__ = 'performance_thresholds'
    
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer)
    application_name = Column(String(100))
    metric_name = Column(String(50))
    threshold_value = Column(Float)
    unit = Column(String(20))
    severity = Column(String(20))


class Incident(Base):
    """Historical incidents."""
    __tablename__ = 'incidents'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer)
    application_name = Column(String(100))
    incident_type = Column(String(50))
    severity = Column(String(20))
    description = Column(Text)
    occurred_at = Column(DateTime)
    resolved_at = Column(DateTime)
    status = Column(String(20))


class MetricBaseline(Base):
    """Pre-computed metric baselines for anomaly detection."""
    __tablename__ = 'metric_baselines'

    id = Column(Integer, primary_key=True)
    application_name = Column(String(100), nullable=False)
    metric_name = Column(String(50), nullable=False)  # cpu, memory, latency, error_rate, request_volume

    # Rolling averages for different time windows
    avg_30d = Column(Float)  # 30-day rolling average
    avg_60d = Column(Float)  # 60-day rolling average
    avg_90d = Column(Float)  # 90-day rolling average
    avg_120d = Column(Float)  # 120-day rolling average

    # Statistical measures for anomaly detection
    stddev_30d = Column(Float)  # Standard deviation (30-day)
    min_30d = Column(Float)  # Minimum value seen in 30 days
    max_30d = Column(Float)  # Maximum value seen in 30 days

    # Current/recent values for comparison
    current_value = Column(Float)

    # Metadata
    unit = Column(String(20))  # percent, ms, count, requests/sec
    last_updated = Column(DateTime, default=datetime.now)


class TrafficPattern(Base):
    """Traffic patterns by hour and day for peak detection."""
    __tablename__ = 'traffic_patterns'

    id = Column(Integer, primary_key=True)
    application_name = Column(String(100), nullable=False)
    metric_name = Column(String(50), nullable=False)  # Usually request_volume or latency

    # Time dimensions
    hour_of_day = Column(Integer)  # 0-23
    day_of_week = Column(Integer)  # 0=Monday, 6=Sunday

    # Aggregated values
    avg_value = Column(Float)
    min_value = Column(Float)
    max_value = Column(Float)
    sample_count = Column(Integer)  # Number of data points used

    # Is this a peak period?
    is_peak = Column(Boolean, default=False)

    last_updated = Column(DateTime, default=datetime.now)


class AvailabilityStats(Base):
    """Application availability statistics."""
    __tablename__ = 'availability_stats'

    id = Column(Integer, primary_key=True)
    application_name = Column(String(100), nullable=False)

    # Availability percentages
    uptime_percent_24h = Column(Float)  # Last 24 hours
    uptime_percent_7d = Column(Float)   # Last 7 days
    uptime_percent_30d = Column(Float)  # Last 30 days

    # Downtime incidents
    total_downtime_minutes_24h = Column(Float)
    total_downtime_minutes_7d = Column(Float)
    total_downtime_minutes_30d = Column(Float)

    # Error-based availability (1 - error_rate)
    error_free_percent_24h = Column(Float)
    error_free_percent_7d = Column(Float)
    error_free_percent_30d = Column(Float)

    # Request success rate
    success_rate_24h = Column(Float)
    success_rate_7d = Column(Float)
    success_rate_30d = Column(Float)

    last_updated = Column(DateTime, default=datetime.now)


class MetricTimeSeries(Base):
    """Historical metric time series data for trend analysis."""
    __tablename__ = 'metric_timeseries'

    id = Column(Integer, primary_key=True)
    application_name = Column(String(100), nullable=False)
    metric_name = Column(String(50), nullable=False)

    timestamp = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)

    # Optional labels
    endpoint = Column(String(200))
    environment = Column(String(50), default='production')


def create_sample_database(db_path: str = 'oracle_pilot.db'):
    """Create sample database with monitoring data."""
    
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Clear existing data
    session.query(Application).delete()
    session.query(PerformanceThreshold).delete()
    session.query(Incident).delete()
    
    # Sample applications
    apps = [
        Application(
            id=1,
            name='user-service',
            environment='production',
            status='active',
            owner='platform-team',
            description='User authentication and profile management service'
        ),
        Application(
            id=2,
            name='payment-gateway',
            environment='production',
            status='active',
            owner='payments-team',
            description='Payment processing and transaction management'
        ),
        Application(
            id=3,
            name='notification-service',
            environment='production',
            status='active',
            owner='platform-team',
            description='Email and push notification delivery service'
        ),
        Application(
            id=4,
            name='analytics-engine',
            environment='production',
            status='active',
            owner='data-team',
            description='Real-time analytics and reporting engine'
        ),
    ]
    
    # Sample thresholds
    thresholds = [
        # user-service thresholds
        PerformanceThreshold(application_id=1, application_name='user-service', 
                           metric_name='cpu_usage', threshold_value=80.0, unit='percent', severity='warning'),
        PerformanceThreshold(application_id=1, application_name='user-service',
                           metric_name='memory_usage', threshold_value=85.0, unit='percent', severity='warning'),
        PerformanceThreshold(application_id=1, application_name='user-service',
                           metric_name='response_time', threshold_value=500.0, unit='ms', severity='critical'),
        PerformanceThreshold(application_id=1, application_name='user-service',
                           metric_name='error_rate', threshold_value=5.0, unit='percent', severity='critical'),
        
        # payment-gateway thresholds (stricter)
        PerformanceThreshold(application_id=2, application_name='payment-gateway',
                           metric_name='cpu_usage', threshold_value=70.0, unit='percent', severity='warning'),
        PerformanceThreshold(application_id=2, application_name='payment-gateway',
                           metric_name='memory_usage', threshold_value=80.0, unit='percent', severity='warning'),
        PerformanceThreshold(application_id=2, application_name='payment-gateway',
                           metric_name='response_time', threshold_value=300.0, unit='ms', severity='critical'),
        PerformanceThreshold(application_id=2, application_name='payment-gateway',
                           metric_name='error_rate', threshold_value=1.0, unit='percent', severity='critical'),
        
        # notification-service thresholds
        PerformanceThreshold(application_id=3, application_name='notification-service',
                           metric_name='cpu_usage', threshold_value=75.0, unit='percent', severity='warning'),
        PerformanceThreshold(application_id=3, application_name='notification-service',
                           metric_name='memory_usage', threshold_value=80.0, unit='percent', severity='warning'),
        
        # analytics-engine thresholds
        PerformanceThreshold(application_id=4, application_name='analytics-engine',
                           metric_name='cpu_usage', threshold_value=90.0, unit='percent', severity='warning'),
        PerformanceThreshold(application_id=4, application_name='analytics-engine',
                           metric_name='memory_usage', threshold_value=90.0, unit='percent', severity='warning'),
    ]
    
    # Sample incidents
    now = datetime.now()
    incidents = [
        Incident(
            application_id=1, application_name='user-service',
            incident_type='high_latency', severity='warning',
            description='Response time exceeded 800ms for login endpoint',
            occurred_at=now - timedelta(hours=2),
            resolved_at=now - timedelta(hours=1, minutes=30),
            status='resolved'
        ),
        Incident(
            application_id=2, application_name='payment-gateway',
            incident_type='error_spike', severity='critical',
            description='401 authentication errors increased by 300%',
            occurred_at=now - timedelta(days=1, hours=5),
            resolved_at=now - timedelta(days=1, hours=4),
            status='resolved'
        ),
        Incident(
            application_id=1, application_name='user-service',
            incident_type='high_cpu', severity='warning',
            description='CPU usage sustained above 85% for 15 minutes',
            occurred_at=now - timedelta(days=3),
            resolved_at=now - timedelta(days=2, hours=23),
            status='resolved'
        ),
        Incident(
            application_id=3, application_name='notification-service',
            incident_type='service_unavailable', severity='critical',
            description='Service returned 503 errors for 5 minutes',
            occurred_at=now - timedelta(days=7),
            resolved_at=now - timedelta(days=6, hours=23),
            status='resolved'
        ),
    ]
    
    # Add all data
    session.add_all(apps)
    session.add_all(thresholds)
    session.add_all(incidents)
    
    session.commit()
    session.close()
    
    return engine


def get_database_engine(db_path: str = None):
    """Get or create database engine."""
    if db_path is None:
        db_path = get_db_path()
    if not os.path.exists(db_path):
        return create_sample_database(db_path)
    # Ensure all tables exist (for migrations)
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    return engine


def get_session(db_path: str = None):
    """Get a database session."""
    engine = get_database_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()
