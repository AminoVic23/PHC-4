"""
Satisfaction models for patient satisfaction surveys
"""
from datetime import datetime, timedelta
from app import db

class Survey(db.Model):
    """Patient satisfaction survey model"""
    __tablename__ = 'surveys'

    id = db.Column(db.Integer, primary_key=True)
    survey_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), index=True)
    survey_type = db.Column(db.String(50), nullable=False, index=True)  # general, specific_visit, follow_up
    survey_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date, index=True)
    overall_rating = db.Column(db.Integer)  # 1-5 scale
    wait_time_rating = db.Column(db.Integer)  # 1-5 scale
    staff_friendliness_rating = db.Column(db.Integer)  # 1-5 scale
    care_quality_rating = db.Column(db.Integer)  # 1-5 scale
    cleanliness_rating = db.Column(db.Integer)  # 1-5 scale
    communication_rating = db.Column(db.Integer)  # 1-5 scale
    would_recommend = db.Column(db.Boolean)  # Would recommend to others
    comments = db.Column(db.Text)
    status = db.Column(db.String(20), default='completed', nullable=False, index=True)  # completed, partial, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref='surveys')
    visit = db.relationship('Visit', backref='surveys')

    def __init__(self, **kwargs):
        super(Survey, self).__init__(**kwargs)
        if not self.survey_no:
            self.survey_no = self.generate_survey_no()

    @property
    def is_completed(self):
        """Check if survey is completed"""
        return self.status == 'completed'

    @property
    def is_partial(self):
        """Check if survey is partially completed"""
        return self.status == 'partial'

    @property
    def is_cancelled(self):
        """Check if survey is cancelled"""
        return self.status == 'cancelled'

    @property
    def average_rating(self):
        """Calculate average rating from all rating fields"""
        ratings = [
            self.overall_rating,
            self.wait_time_rating,
            self.staff_friendliness_rating,
            self.care_quality_rating,
            self.cleanliness_rating,
            self.communication_rating
        ]
        valid_ratings = [r for r in ratings if r is not None]
        return sum(valid_ratings) / len(valid_ratings) if valid_ratings else None

    @property
    def nps_score(self):
        """Calculate Net Promoter Score (NPS)"""
        if self.overall_rating is None:
            return None
        
        if self.overall_rating >= 9:
            return 'Promoter'
        elif self.overall_rating >= 7:
            return 'Passive'
        else:
            return 'Detractor'

    @property
    def nps_category(self):
        """Get NPS category for analysis"""
        nps = self.nps_score
        if nps == 'Promoter':
            return 1
        elif nps == 'Passive':
            return 0
        elif nps == 'Detractor':
            return -1
        return None

    @property
    def satisfaction_level(self):
        """Get satisfaction level based on average rating"""
        avg = self.average_rating
        if avg is None:
            return 'Not Rated'
        elif avg >= 4.5:
            return 'Very Satisfied'
        elif avg >= 4.0:
            return 'Satisfied'
        elif avg >= 3.0:
            return 'Neutral'
        elif avg >= 2.0:
            return 'Dissatisfied'
        else:
            return 'Very Dissatisfied'

    def calculate_overall_rating(self):
        """Calculate overall rating from other ratings"""
        ratings = [
            self.wait_time_rating,
            self.staff_friendliness_rating,
            self.care_quality_rating,
            self.cleanliness_rating,
            self.communication_rating
        ]
        valid_ratings = [r for r in ratings if r is not None]
        if valid_ratings:
            self.overall_rating = round(sum(valid_ratings) / len(valid_ratings))

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'survey_no': self.survey_no,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else None,
            'visit_id': self.visit_id,
            'visit_no': self.visit.visit_no if self.visit else None,
            'survey_type': self.survey_type,
            'survey_date': self.survey_date.isoformat() if self.survey_date else None,
            'overall_rating': self.overall_rating,
            'wait_time_rating': self.wait_time_rating,
            'staff_friendliness_rating': self.staff_friendliness_rating,
            'care_quality_rating': self.care_quality_rating,
            'cleanliness_rating': self.cleanliness_rating,
            'communication_rating': self.communication_rating,
            'would_recommend': self.would_recommend,
            'comments': self.comments,
            'status': self.status,
            'average_rating': self.average_rating,
            'nps_score': self.nps_score,
            'nps_category': self.nps_category,
            'satisfaction_level': self.satisfaction_level,
            'is_completed': self.is_completed,
            'is_partial': self.is_partial,
            'is_cancelled': self.is_cancelled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Survey {self.survey_no}: {self.patient.full_name if self.patient else "Unknown"} ({self.overall_rating}/5)>'

    @classmethod
    def generate_survey_no(cls):
        """Generate a unique survey number"""
        import random
        import string

        while True:
            # Generate survey number in format: SUR-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            survey_no = f"SUR-{date_str}-{digits}"

            # Check if survey number already exists
            if not cls.query.filter_by(survey_no=survey_no).first():
                return survey_no

    @classmethod
    def get_completed_surveys(cls, limit=50):
        """Get completed surveys"""
        return cls.query.filter_by(status='completed')\
                       .order_by(cls.survey_date.desc())\
                       .limit(limit).all()

    @classmethod
    def get_patient_surveys(cls, patient_id, limit=20):
        """Get surveys for a patient"""
        return cls.query.filter_by(patient_id=patient_id)\
                       .order_by(cls.survey_date.desc())\
                       .limit(limit).all()

    @classmethod
    def get_visit_surveys(cls, visit_id):
        """Get surveys for a specific visit"""
        return cls.query.filter_by(visit_id=visit_id)\
                       .order_by(cls.survey_date.desc()).all()

    @classmethod
    def get_surveys_by_type(cls, survey_type, limit=50):
        """Get surveys by type"""
        return cls.query.filter_by(survey_type=survey_type)\
                       .order_by(cls.survey_date.desc())\
                       .limit(limit).all()

    @classmethod
    def get_recent_surveys(cls, days=30):
        """Get recent surveys"""
        cutoff_date = datetime.now().date() - timedelta(days=days)
        return cls.query.filter(
            cls.survey_date >= cutoff_date,
            cls.status == 'completed'
        ).order_by(cls.survey_date.desc()).all()

    @classmethod
    def get_high_rating_surveys(cls, min_rating=4, limit=50):
        """Get surveys with high ratings"""
        return cls.query.filter(
            cls.overall_rating >= min_rating,
            cls.status == 'completed'
        ).order_by(cls.overall_rating.desc(), cls.survey_date.desc())\
         .limit(limit).all()

    @classmethod
    def get_low_rating_surveys(cls, max_rating=2, limit=50):
        """Get surveys with low ratings"""
        return cls.query.filter(
            cls.overall_rating <= max_rating,
            cls.status == 'completed'
        ).order_by(cls.overall_rating.asc(), cls.survey_date.desc())\
         .limit(limit).all()

    @classmethod
    def get_nps_promoters(cls, limit=50):
        """Get surveys from promoters (NPS 9-10)"""
        return cls.query.filter(
            cls.overall_rating >= 9,
            cls.status == 'completed'
        ).order_by(cls.survey_date.desc())\
         .limit(limit).all()

    @classmethod
    def get_nps_detractors(cls, limit=50):
        """Get surveys from detractors (NPS 0-6)"""
        return cls.query.filter(
            cls.overall_rating <= 6,
            cls.status == 'completed'
        ).order_by(cls.survey_date.desc())\
         .limit(limit).all()

    @classmethod
    def get_survey_statistics(cls, days=30):
        """Get survey statistics"""
        cutoff_date = datetime.now().date() - timedelta(days=days)
        
        # Get surveys in date range
        surveys = cls.query.filter(
            cls.survey_date >= cutoff_date,
            cls.status == 'completed'
        ).all()
        
        if not surveys:
            return {
                'total_surveys': 0,
                'average_rating': 0,
                'nps_score': 0,
                'promoters': 0,
                'passives': 0,
                'detractors': 0,
                'recommendation_rate': 0
            }
        
        # Calculate statistics
        total_surveys = len(surveys)
        average_rating = sum(s.overall_rating for s in surveys if s.overall_rating) / total_surveys
        
        promoters = len([s for s in surveys if s.nps_category == 1])
        passives = len([s for s in surveys if s.nps_category == 0])
        detractors = len([s for s in surveys if s.nps_category == -1])
        
        nps_score = ((promoters - detractors) / total_surveys) * 100 if total_surveys > 0 else 0
        
        would_recommend = len([s for s in surveys if s.would_recommend])
        recommendation_rate = (would_recommend / total_surveys) * 100 if total_surveys > 0 else 0
        
        return {
            'total_surveys': total_surveys,
            'average_rating': round(average_rating, 2),
            'nps_score': round(nps_score, 1),
            'promoters': promoters,
            'passives': passives,
            'detractors': detractors,
            'recommendation_rate': round(recommendation_rate, 1)
        }

    @classmethod
    def get_rating_distribution(cls, days=30):
        """Get rating distribution"""
        cutoff_date = datetime.now().date() - timedelta(days=days)
        
        surveys = cls.query.filter(
            cls.survey_date >= cutoff_date,
            cls.status == 'completed',
            cls.overall_rating.isnot(None)
        ).all()
        
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for survey in surveys:
            if survey.overall_rating in distribution:
                distribution[survey.overall_rating] += 1
        
        return distribution

    @classmethod
    def get_satisfaction_trends(cls, days=90):
        """Get satisfaction trends over time"""
        cutoff_date = datetime.now().date() - timedelta(days=days)
        
        surveys = cls.query.filter(
            cls.survey_date >= cutoff_date,
            cls.status == 'completed',
            cls.overall_rating.isnot(None)
        ).order_by(cls.survey_date).all()
        
        trends = {}
        for survey in surveys:
            date_str = survey.survey_date.isoformat()
            if date_str not in trends:
                trends[date_str] = {'count': 0, 'total_rating': 0}
            
            trends[date_str]['count'] += 1
            trends[date_str]['total_rating'] += survey.overall_rating
        
        # Calculate averages
        for date_str in trends:
            trends[date_str]['average_rating'] = trends[date_str]['total_rating'] / trends[date_str]['count']
        
        return trends
