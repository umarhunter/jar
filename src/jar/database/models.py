"""
Oracle database setup with sample schema for application monitoring.
Uses SQLite for the pilot phase to simulate Oracle database.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import random

Base = declarative_base()


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


def get_database_engine(db_path: str = 'oracle_pilot.db'):
    """Get or create database engine."""
    import os
    if not os.path.exists(db_path):
        return create_sample_database(db_path)
    return create_engine(f'sqlite:///{db_path}')
