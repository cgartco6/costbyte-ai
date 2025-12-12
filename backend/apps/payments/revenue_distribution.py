# backend/apps/payments/revenue_distribution.py
class RevenueDistributor:
    
    DISTRIBUTION = {
        'owner_fnb': 0.35,      # 35% to owner FNB
        'african_bank': 0.15,   # 15% to African Bank
        'ai_fnb': 0.20,         # 20% to AI development FNB
        'reserve_fnb': 0.20,    # 20% to reserve account
        'growth_account': 0.10  # 10% stays and grows weekly
    }
    
    def distribute_weekly(self):
        """Weekly payout distribution"""
        weekly_revenue = self.calculate_weekly_revenue()
        
        distributions = {}
        for account, percentage in self.DISTRIBUTION.items():
            amount = weekly_revenue * percentage
            
            if account == 'growth_account':
                # Reinvest with 10% weekly growth
                amount = amount * 1.10
                self.reinvest_growth_fund(amount)
            else:
                self.transfer_to_account(account, amount)
                
            distributions[account] = amount
            
        return distributions
