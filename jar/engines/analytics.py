"""
Custom Analytics Engine for LlamaIndex.
Provides real-time anomaly detection, trend analysis, and pattern recognition
using pre-computed baselines and custom calculation functions.
"""
from typing import Any, Optional, List, Dict
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.prompts import PromptTemplate
from llama_index.core.llms.llm import BaseLLM
from sqlalchemy import text
from datetime import datetime, timedelta
import math
import os

from jar.database.models import (
    get_session, get_db_path,
    MetricBaseline, TrafficPattern, AvailabilityStats, MetricTimeSeries
)


ANALYTICS_QUERY_PROMPT = PromptTemplate(
    "You are an expert in observability analytics and anomaly detection.\n"
    "Given a natural language query about metrics analysis, determine what analysis to perform.\n\n"
    "Available analysis types:\n"
    "- anomaly_detection: Check if a metric is abnormal compared to historical baselines\n"
    "- trend_analysis: Analyze metric trends over time\n"
    "- baseline_comparison: Compare current values to 30/60/90/120 day averages\n"
    "- peak_detection: Find peak traffic times and patterns\n"
    "- availability_check: Get availability and uptime statistics\n"
    "- pattern_recognition: Identify daily/weekly patterns\n"
    "- historical_extremes: Find highest/lowest values across entire historical time range (120 days)\n\n"
    "Applications: user-service, payment-gateway, notification-service, metric-analysis\n"
    "Metrics: cpu, memory, latency, request_volume, error_rate\n\n"
    "Query: {query_str}\n\n"
    "Respond ONLY with valid JSON using DOUBLE QUOTES:\n"
    "{{\n"
    "  \"analysis_type\": \"<anomaly_detection|trend_analysis|baseline_comparison|peak_detection|availability_check|pattern_recognition|historical_extremes>\",\n"
    "  \"metric\": \"<cpu|memory|latency|request_volume|error_rate|all>\",\n"
    "  \"application\": \"<application name or 'all'>\",\n"
    "  \"time_window_days\": <30|60|90|120>,\n"
    "  \"comparison_type\": \"<current_vs_average|current_vs_stddev|trend>\",\n"
    "  \"extreme_type\": \"<max|min|both>\"\n"
    "}}\n\n"
    "Response:"
)


class AnalyticsQueryEngine(CustomQueryEngine):
    """Custom query engine for analytics, anomaly detection, and pattern recognition."""

    llm: BaseLLM
    db_path: str = ""
    progress_callback: Any = None

    def __init__(self, llm: BaseLLM, db_path: Optional[str] = None,
                 progress_callback: Any = None, **kwargs):
        """
        Initialize Analytics query engine.

        Args:
            llm: LLM instance
            db_path: Path to SQLite database
            progress_callback: Optional callback for progress updates
        """
        if db_path is None:
            db_path = get_db_path()

        super().__init__(llm=llm, db_path=db_path, progress_callback=progress_callback, **kwargs)
        print(f"Analytics engine initialized with database at {db_path}")

    def _emit_progress(self, step: str, message: str, reasoning: str = ""):
        """Emit progress update if callback is provided."""
        if self.progress_callback:
            self.progress_callback({
                'step': step,
                'message': message,
                'source': 'analytics',
                'reasoning': reasoning
            })

    def custom_query(self, query_str: str) -> Any:
        """Execute an analytics query."""
        self._emit_progress('query_start', 'Analyzing query for analytics...',
                           'Determining analysis type and parameters')

        # Parse the query using LLM
        prompt = ANALYTICS_QUERY_PROMPT.format(query_str=query_str)
        response = self.llm.complete(prompt)

        try:
            import json
            from jar.engines.utils import parse_llm_json_response
            response_text = parse_llm_json_response(response.text)
            query_info = json.loads(response_text)

            analysis_type = query_info.get('analysis_type', 'baseline_comparison')
            metric = query_info.get('metric', 'all')
            application = query_info.get('application', 'all')
            time_window = query_info.get('time_window_days', 30)
            comparison_type = query_info.get('comparison_type', 'current_vs_average')

        except Exception as e:
            print(f"Warning: Failed to parse analytics query: {e}")
            # Smart defaults based on keywords
            query_lower = query_str.lower()

            # Detect analysis type based on keywords
            if 'highest' in query_lower or 'lowest' in query_lower or 'maximum' in query_lower or 'minimum' in query_lower or 'ever' in query_lower or 'at any point' in query_lower:
                analysis_type = 'historical_extremes'
            elif 'anomaly' in query_lower or 'abnormal' in query_lower:
                analysis_type = 'anomaly_detection'
            elif 'trend' in query_lower:
                analysis_type = 'trend_analysis'
            elif 'peak' in query_lower or 'traffic time' in query_lower:
                analysis_type = 'peak_detection'
            elif 'availability' in query_lower or 'uptime' in query_lower:
                analysis_type = 'availability_check'
            elif 'pattern' in query_lower:
                analysis_type = 'pattern_recognition'
            else:
                analysis_type = 'baseline_comparison'

            metric = 'all'
            application = 'all'
            time_window = 120  # Default to full historical range
            comparison_type = 'current_vs_average'

            # Try to extract application name
            for app in ['user-service', 'payment-gateway', 'notification-service', 'metric-analysis']:
                if app.replace('-', ' ') in query_lower or app in query_lower:
                    application = app
                    break

            # Try to extract metric
            if 'cpu' in query_lower:
                metric = 'cpu'
            elif 'memory' in query_lower:
                metric = 'memory'
            elif 'latency' in query_lower or 'response time' in query_lower:
                metric = 'latency'
            elif 'error' in query_lower:
                metric = 'error_rate'
            elif 'request' in query_lower or 'traffic' in query_lower or 'volume' in query_lower:
                metric = 'request_volume'

        self._emit_progress('analysis_type', f'Performing {analysis_type}',
                           f'Analyzing {metric} for {application}')

        # Route to appropriate analysis function
        if analysis_type == 'anomaly_detection':
            results = self._detect_anomalies(application, metric, time_window)
        elif analysis_type == 'trend_analysis':
            results = self._analyze_trends(application, metric, time_window)
        elif analysis_type == 'peak_detection':
            results = self._detect_peaks(application, metric)
        elif analysis_type == 'availability_check':
            results = self._check_availability(application)
        elif analysis_type == 'pattern_recognition':
            results = self._recognize_patterns(application, metric)
        elif analysis_type == 'historical_extremes':
            results = self._find_historical_extremes(application, metric, time_window)
        else:  # baseline_comparison
            results = self._compare_baselines(application, metric, time_window)

        self._emit_progress('query_complete', 'Analytics query complete',
                           f'Completed {analysis_type} analysis')

        return {
            'query': query_str,
            'analysis_type': analysis_type,
            'metric': metric,
            'application': application,
            'time_window_days': time_window,
            'results': results,
            'summary': self._generate_summary(results, analysis_type)
        }

    def _detect_anomalies(self, application: str, metric: str, time_window: int) -> Dict:
        """Detect anomalies by comparing current values to historical baselines."""
        session = get_session(self.db_path)
        try:
            query = session.query(MetricBaseline)
            if application != 'all':
                query = query.filter(MetricBaseline.application_name == application)
            if metric != 'all':
                query = query.filter(MetricBaseline.metric_name == metric)

            baselines = query.all()
            anomalies = []

            for baseline in baselines:
                current = baseline.current_value
                avg = getattr(baseline, f'avg_{time_window}d', baseline.avg_30d) or baseline.avg_30d
                stddev = baseline.stddev_30d or 0

                # Calculate z-score (how many standard deviations from mean)
                if stddev > 0:
                    z_score = abs(current - avg) / stddev
                else:
                    z_score = 0

                # Determine if anomalous (z-score > 2 is typically considered anomalous)
                is_anomaly = z_score > 2
                severity = 'normal'
                if z_score > 3:
                    severity = 'critical'
                elif z_score > 2:
                    severity = 'warning'

                anomalies.append({
                    'application': baseline.application_name,
                    'metric': baseline.metric_name,
                    'current_value': round(current, 2),
                    'baseline_avg': round(avg, 2),
                    'stddev': round(stddev, 2),
                    'z_score': round(z_score, 2),
                    'is_anomaly': is_anomaly,
                    'severity': severity,
                    'unit': baseline.unit,
                    'deviation_percent': round(((current - avg) / avg * 100) if avg else 0, 1)
                })

            return {
                'anomalies': [a for a in anomalies if a['is_anomaly']],
                'all_metrics': anomalies,
                'total_anomalies': sum(1 for a in anomalies if a['is_anomaly']),
                'analysis_window': f'{time_window} days'
            }
        finally:
            session.close()

    def _compare_baselines(self, application: str, metric: str, time_window: int) -> Dict:
        """Compare current values against historical baselines."""
        session = get_session(self.db_path)
        try:
            query = session.query(MetricBaseline)
            if application != 'all':
                query = query.filter(MetricBaseline.application_name == application)
            if metric != 'all':
                query = query.filter(MetricBaseline.metric_name == metric)

            baselines = query.all()
            comparisons = []

            for baseline in baselines:
                current = baseline.current_value

                comparisons.append({
                    'application': baseline.application_name,
                    'metric': baseline.metric_name,
                    'current_value': round(current, 2),
                    'avg_30d': round(baseline.avg_30d or 0, 2),
                    'avg_60d': round(baseline.avg_60d or 0, 2),
                    'avg_90d': round(baseline.avg_90d or 0, 2),
                    'avg_120d': round(baseline.avg_120d or 0, 2),
                    'min_30d': round(baseline.min_30d or 0, 2),
                    'max_30d': round(baseline.max_30d or 0, 2),
                    'stddev_30d': round(baseline.stddev_30d or 0, 2),
                    'unit': baseline.unit,
                    'vs_30d_percent': round(((current - (baseline.avg_30d or 0)) / (baseline.avg_30d or 1) * 100), 1),
                    'last_updated': baseline.last_updated.isoformat() if baseline.last_updated else None
                })

            return {
                'comparisons': comparisons,
                'comparison_window': f'{time_window} days'
            }
        finally:
            session.close()

    def _analyze_trends(self, application: str, metric: str, time_window: int) -> Dict:
        """Analyze metric trends over time using stored time series data."""
        session = get_session(self.db_path)
        try:
            cutoff = datetime.now() - timedelta(days=time_window)

            query = session.query(MetricTimeSeries).filter(
                MetricTimeSeries.timestamp >= cutoff
            )
            if application != 'all':
                query = query.filter(MetricTimeSeries.application_name == application)
            if metric != 'all':
                query = query.filter(MetricTimeSeries.metric_name == metric)

            query = query.order_by(MetricTimeSeries.timestamp)
            data_points = query.all()

            if not data_points:
                return {'error': 'No time series data available', 'trends': []}

            # Group by application and metric
            grouped = {}
            for dp in data_points:
                key = (dp.application_name, dp.metric_name)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append({'timestamp': dp.timestamp, 'value': dp.value})

            trends = []
            for (app, met), points in grouped.items():
                if len(points) < 2:
                    continue

                values = [p['value'] for p in points]
                first_half = values[:len(values)//2]
                second_half = values[len(values)//2:]

                avg_first = sum(first_half) / len(first_half)
                avg_second = sum(second_half) / len(second_half)

                trend_direction = 'increasing' if avg_second > avg_first else 'decreasing' if avg_second < avg_first else 'stable'
                trend_percent = ((avg_second - avg_first) / avg_first * 100) if avg_first else 0

                trends.append({
                    'application': app,
                    'metric': met,
                    'trend': trend_direction,
                    'change_percent': round(trend_percent, 1),
                    'period_start_avg': round(avg_first, 2),
                    'period_end_avg': round(avg_second, 2),
                    'data_points': len(points),
                    'min_value': round(min(values), 2),
                    'max_value': round(max(values), 2)
                })

            return {
                'trends': trends,
                'analysis_window': f'{time_window} days',
                'total_data_points': len(data_points)
            }
        finally:
            session.close()

    def _detect_peaks(self, application: str, metric: str = 'request_volume') -> Dict:
        """Detect peak traffic times and patterns."""
        session = get_session(self.db_path)
        try:
            query = session.query(TrafficPattern).filter(
                TrafficPattern.is_peak == True
            )
            if application != 'all':
                query = query.filter(TrafficPattern.application_name == application)
            if metric != 'all':
                query = query.filter(TrafficPattern.metric_name == metric)

            peaks = query.all()

            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

            peak_times = []
            for peak in peaks:
                peak_times.append({
                    'application': peak.application_name,
                    'metric': peak.metric_name,
                    'hour': peak.hour_of_day,
                    'hour_formatted': f'{peak.hour_of_day:02d}:00',
                    'day_of_week': peak.day_of_week,
                    'day_name': day_names[peak.day_of_week],
                    'avg_value': round(peak.avg_value, 2),
                    'max_value': round(peak.max_value, 2)
                })

            # Summarize peak hours
            peak_hours = {}
            for p in peak_times:
                hour = p['hour']
                if hour not in peak_hours:
                    peak_hours[hour] = 0
                peak_hours[hour] += 1

            most_common_peaks = sorted(peak_hours.items(), key=lambda x: x[1], reverse=True)[:3]

            return {
                'peak_times': peak_times,
                'most_common_peak_hours': [f'{h:02d}:00' for h, _ in most_common_peaks],
                'total_peak_periods': len(peak_times),
                'summary': f"Peak traffic typically occurs around {', '.join(f'{h:02d}:00' for h, _ in most_common_peaks[:2])}"
            }
        finally:
            session.close()

    def _check_availability(self, application: str) -> Dict:
        """Get availability and uptime statistics."""
        session = get_session(self.db_path)
        try:
            query = session.query(AvailabilityStats)
            if application != 'all':
                query = query.filter(AvailabilityStats.application_name == application)

            stats = query.all()
            availability = []

            for stat in stats:
                availability.append({
                    'application': stat.application_name,
                    'uptime_24h': round(stat.uptime_percent_24h or 0, 2),
                    'uptime_7d': round(stat.uptime_percent_7d or 0, 2),
                    'uptime_30d': round(stat.uptime_percent_30d or 0, 2),
                    'downtime_24h_minutes': round(stat.total_downtime_minutes_24h or 0, 1),
                    'downtime_7d_minutes': round(stat.total_downtime_minutes_7d or 0, 1),
                    'downtime_30d_minutes': round(stat.total_downtime_minutes_30d or 0, 1),
                    'error_free_24h': round(stat.error_free_percent_24h or 0, 2),
                    'error_free_7d': round(stat.error_free_percent_7d or 0, 2),
                    'error_free_30d': round(stat.error_free_percent_30d or 0, 2),
                    'success_rate_24h': round(stat.success_rate_24h or 0, 2),
                    'success_rate_7d': round(stat.success_rate_7d or 0, 2),
                    'success_rate_30d': round(stat.success_rate_30d or 0, 2),
                    'last_updated': stat.last_updated.isoformat() if stat.last_updated else None
                })

            # Calculate overall averages
            if availability:
                avg_uptime_24h = sum(a['uptime_24h'] for a in availability) / len(availability)
                avg_uptime_7d = sum(a['uptime_7d'] for a in availability) / len(availability)
                avg_uptime_30d = sum(a['uptime_30d'] for a in availability) / len(availability)
            else:
                avg_uptime_24h = avg_uptime_7d = avg_uptime_30d = 0

            return {
                'availability': availability,
                'overall_uptime_24h': round(avg_uptime_24h, 2),
                'overall_uptime_7d': round(avg_uptime_7d, 2),
                'overall_uptime_30d': round(avg_uptime_30d, 2)
            }
        finally:
            session.close()

    def _find_historical_extremes(self, application: str, metric: str, time_window: int) -> Dict:
        """Find the highest/lowest values across entire historical time range."""
        session = get_session(self.db_path)
        try:
            cutoff = datetime.now() - timedelta(days=time_window)

            query = session.query(MetricTimeSeries).filter(
                MetricTimeSeries.timestamp >= cutoff
            )
            if application != 'all':
                query = query.filter(MetricTimeSeries.application_name == application)
            if metric != 'all':
                query = query.filter(MetricTimeSeries.metric_name == metric)

            data_points = query.all()

            if not data_points:
                return {'error': 'No historical data available', 'extremes': []}

            # Group by application and metric
            grouped = {}
            for dp in data_points:
                key = (dp.application_name, dp.metric_name)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append({
                    'timestamp': dp.timestamp,
                    'value': dp.value
                })

            extremes = []
            for (app, met), points in grouped.items():
                values = [p['value'] for p in points]
                max_point = max(points, key=lambda p: p['value'])
                min_point = min(points, key=lambda p: p['value'])

                # Get unit from baselines
                baseline = session.query(MetricBaseline).filter(
                    MetricBaseline.application_name == app,
                    MetricBaseline.metric_name == met
                ).first()
                unit = baseline.unit if baseline else ''

                extremes.append({
                    'application': app,
                    'metric': met,
                    'max_value': round(max_point['value'], 2),
                    'max_timestamp': max_point['timestamp'].isoformat(),
                    'min_value': round(min_point['value'], 2),
                    'min_timestamp': min_point['timestamp'].isoformat(),
                    'avg_value': round(sum(values) / len(values), 2),
                    'data_points': len(points),
                    'unit': unit
                })

            return {
                'extremes': extremes,
                'time_window': f'{time_window} days',
                'total_data_points': len(data_points)
            }
        finally:
            session.close()

    def _recognize_patterns(self, application: str, metric: str = 'request_volume') -> Dict:
        """Recognize daily and weekly patterns."""
        session = get_session(self.db_path)
        try:
            query = session.query(TrafficPattern)
            if application != 'all':
                query = query.filter(TrafficPattern.application_name == application)
            if metric != 'all':
                query = query.filter(TrafficPattern.metric_name == metric)

            patterns = query.all()

            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

            # Aggregate by hour (across all days)
            hourly_pattern = {}
            for p in patterns:
                hour = p.hour_of_day
                if hour not in hourly_pattern:
                    hourly_pattern[hour] = []
                hourly_pattern[hour].append(p.avg_value)

            hourly_averages = [
                {'hour': h, 'hour_formatted': f'{h:02d}:00', 'avg_value': round(sum(v)/len(v), 2)}
                for h, v in sorted(hourly_pattern.items())
            ]

            # Aggregate by day of week
            daily_pattern = {}
            for p in patterns:
                day = p.day_of_week
                if day not in daily_pattern:
                    daily_pattern[day] = []
                daily_pattern[day].append(p.avg_value)

            daily_averages = [
                {'day': d, 'day_name': day_names[d], 'avg_value': round(sum(v)/len(v), 2)}
                for d, v in sorted(daily_pattern.items())
            ]

            # Identify patterns
            if hourly_averages:
                max_hour = max(hourly_averages, key=lambda x: x['avg_value'])
                min_hour = min(hourly_averages, key=lambda x: x['avg_value'])
            else:
                max_hour = min_hour = {'hour_formatted': 'N/A', 'avg_value': 0}

            if daily_averages:
                max_day = max(daily_averages, key=lambda x: x['avg_value'])
                min_day = min(daily_averages, key=lambda x: x['avg_value'])
            else:
                max_day = min_day = {'day_name': 'N/A', 'avg_value': 0}

            return {
                'hourly_pattern': hourly_averages,
                'daily_pattern': daily_averages,
                'peak_hour': max_hour['hour_formatted'],
                'lowest_hour': min_hour['hour_formatted'],
                'busiest_day': max_day['day_name'],
                'quietest_day': min_day['day_name'],
                'pattern_summary': f"Highest activity at {max_hour['hour_formatted']} on {max_day['day_name']}s, "
                                  f"lowest at {min_hour['hour_formatted']} on {min_day['day_name']}s"
            }
        finally:
            session.close()

    def _generate_summary(self, results: Dict, analysis_type: str) -> str:
        """Generate a human-readable summary of the analysis results."""
        if analysis_type == 'anomaly_detection':
            total = results.get('total_anomalies', 0)
            all_metrics = results.get('all_metrics', [])

            if total == 0:
                # Enhanced response: show baseline context even when no anomalies
                summary_parts = ["No anomalies detected. All metrics are within normal ranges (±2 standard deviations from baseline)."]

                if all_metrics:
                    summary_parts.append("\nCurrent values compared to baseline:")
                    for m in all_metrics[:5]:  # Show up to 5 metrics
                        direction = "above" if m['deviation_percent'] > 0 else "below" if m['deviation_percent'] < 0 else "at"
                        summary_parts.append(
                            f"  - {m['application']}/{m['metric']}: {m['current_value']}{m['unit']} "
                            f"({abs(m['deviation_percent']):.1f}% {direction} baseline avg of {m['baseline_avg']}{m['unit']}, "
                            f"z-score: {m['z_score']})"
                        )

                    # Add note about expected patterns
                    summary_parts.append("\nNote: Metrics naturally fluctuate due to daily/weekly traffic patterns. "
                                       "Values within normal ranges indicate expected behavior.")

                return "\n".join(summary_parts)
            else:
                anomalies = results.get('anomalies', [])
                summary_parts = [f"Detected {total} anomalies:"]
                for a in anomalies[:3]:  # Show top 3
                    summary_parts.append(
                        f"  - {a['application']}/{a['metric']}: {a['current_value']}{a['unit']} "
                        f"({a['deviation_percent']:+.1f}% from baseline, {a['severity']})"
                    )
                return "\n".join(summary_parts)

        elif analysis_type == 'baseline_comparison':
            comparisons = results.get('comparisons', [])
            if not comparisons:
                return "No baseline data available for comparison."
            summary_parts = [f"Baseline comparison ({results.get('comparison_window', '30 days')}):"]
            for c in comparisons[:5]:
                direction = "above" if c['vs_30d_percent'] > 0 else "below"
                summary_parts.append(
                    f"  - {c['application']}/{c['metric']}: {c['current_value']}{c['unit']} "
                    f"({abs(c['vs_30d_percent']):.1f}% {direction} 30-day avg of {c['avg_30d']})"
                )
            return "\n".join(summary_parts)

        elif analysis_type == 'trend_analysis':
            trends = results.get('trends', [])
            if not trends:
                return "No trend data available."
            summary_parts = ["Trend analysis:"]
            for t in trends[:5]:
                summary_parts.append(
                    f"  - {t['application']}/{t['metric']}: {t['trend']} ({t['change_percent']:+.1f}%)"
                )
            return "\n".join(summary_parts)

        elif analysis_type == 'peak_detection':
            return results.get('summary', 'No peak data available.')

        elif analysis_type == 'availability_check':
            availability = results.get('availability', [])
            if not availability:
                return "No availability data available."
            summary_parts = ["Availability status:"]
            for a in availability:
                summary_parts.append(
                    f"  - {a['application']}: {a['uptime_24h']}% (24h), {a['uptime_7d']}% (7d), {a['uptime_30d']}% (30d)"
                )
            return "\n".join(summary_parts)

        elif analysis_type == 'pattern_recognition':
            return results.get('pattern_summary', 'No pattern data available.')

        elif analysis_type == 'historical_extremes':
            extremes = results.get('extremes', [])
            if not extremes:
                return "No historical data available."
            summary_parts = [f"Historical extremes across {results.get('time_window', '120 days')}:"]
            for e in extremes:
                summary_parts.append(
                    f"  - {e['application']}/{e['metric']}: "
                    f"Max: {e['max_value']}{e['unit']} (at {e['max_timestamp']}), "
                    f"Min: {e['min_value']}{e['unit']} (at {e['min_timestamp']})"
                )
            return "\n".join(summary_parts)

        return "Analysis complete."


# Standalone utility functions that can be called directly

def calculate_anomaly_score(application: str, metric: str, current_value: float,
                           db_path: str = None) -> Dict:
    """
    Calculate anomaly score for a given metric value.
    Can be called directly without going through LLM.
    """
    if db_path is None:
        db_path = get_db_path()

    session = get_session(db_path)
    try:
        baseline = session.query(MetricBaseline).filter(
            MetricBaseline.application_name == application,
            MetricBaseline.metric_name == metric
        ).first()

        if not baseline:
            return {'error': f'No baseline found for {application}/{metric}'}

        avg = baseline.avg_30d or 0
        stddev = baseline.stddev_30d or 1

        z_score = abs(current_value - avg) / stddev if stddev > 0 else 0

        return {
            'application': application,
            'metric': metric,
            'current_value': current_value,
            'baseline_avg': avg,
            'stddev': stddev,
            'z_score': round(z_score, 2),
            'is_anomaly': z_score > 2,
            'severity': 'critical' if z_score > 3 else 'warning' if z_score > 2 else 'normal',
            'deviation_percent': round(((current_value - avg) / avg * 100) if avg else 0, 1)
        }
    finally:
        session.close()


def get_baseline_for_metric(application: str, metric: str, window_days: int = 30,
                            db_path: str = None) -> Dict:
    """
    Get baseline statistics for a specific metric.
    Can be called directly without going through LLM.
    """
    if db_path is None:
        db_path = get_db_path()

    session = get_session(db_path)
    try:
        baseline = session.query(MetricBaseline).filter(
            MetricBaseline.application_name == application,
            MetricBaseline.metric_name == metric
        ).first()

        if not baseline:
            return {'error': f'No baseline found for {application}/{metric}'}

        return {
            'application': application,
            'metric': metric,
            f'avg_{window_days}d': getattr(baseline, f'avg_{window_days}d', baseline.avg_30d),
            'stddev': baseline.stddev_30d,
            'min': baseline.min_30d,
            'max': baseline.max_30d,
            'current': baseline.current_value,
            'unit': baseline.unit
        }
    finally:
        session.close()


def get_peak_hours(application: str, metric: str = 'request_volume',
                  db_path: str = None) -> List[Dict]:
    """
    Get peak hours for an application.
    Can be called directly without going through LLM.
    """
    if db_path is None:
        db_path = get_db_path()

    session = get_session(db_path)
    try:
        peaks = session.query(TrafficPattern).filter(
            TrafficPattern.application_name == application,
            TrafficPattern.metric_name == metric,
            TrafficPattern.is_peak == True
        ).all()

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        return [
            {
                'hour': p.hour_of_day,
                'hour_formatted': f'{p.hour_of_day:02d}:00',
                'day': day_names[p.day_of_week],
                'avg_value': round(p.avg_value, 2)
            }
            for p in peaks
        ]
    finally:
        session.close()
