# backend/apps/dashboard/views.py
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

class OwnerDashboardView(APIView):
    permission_classes = [IsOwner]
    
    def get(self, request):
        # Revenue analytics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        revenue_data = {
            'total_revenue': Payment.objects.filter(
                status='completed'
            ).aggregate(Sum('amount'))['amount__sum'],
            
            'weekly_revenue': Payment.objects.filter(
                status='completed',
                created_at__gte=week_ago
            ).aggregate(Sum('amount'))['amount__sum'],
            
            'user_growth': User.objects.filter(
                date_joined__gte=week_ago
            ).count(),
            
            'application_stats': {
                'total': JobApplication.objects.count(),
                'today': JobApplication.objects.filter(
                    created_at__date=today
                ).count(),
                'success_rate': self.calculate_success_rate()
            }
        }
        
        return Response(revenue_data)
    
    def calculate_success_rate(self):
        # Calculate application success rate
        total = JobApplication.objects.count()
        interviews = JobApplication.objects.filter(
            status__in=['interview', 'offer']
        ).count()
        
        return (interviews / total * 100) if total > 0 else 0
