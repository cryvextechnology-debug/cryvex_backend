import math
from pydantic import BaseModel, Field

class ROIRequest(BaseModel):
    traffic: float = Field(..., ge=0)
    conv_rate: float = Field(..., ge=0, le=100)
    lead_value: float = Field(..., ge=0)
    hourly_rate: float = Field(..., ge=0)
    manual_hours: float = Field(..., ge=0)
    visitor_id: str = Field(default="Unknown", max_length=128)
    business_name: str = Field(default="Unknown", max_length=256)
    industry: str = Field(default="General", max_length=100)
    language: str = Field(default="english", max_length=50)

class CryvexROIEngine:
    def get_pricing_tier(self, traffic):
        """
        Assigns a fixed subscription cost based on the business's lead volume (visitors).
        """
        if traffic < 150:
            return 1500, "STARTUP", "24/7 FAQ & Lead Capture for local boutiques/shops."
        elif traffic <= 500:
            return 4900, "GROWTH", "Lead Qualification & CRM Integration for mid-sized agencies."
        else:
            return 15000, "ENTERPRISE", "Custom Training, Multi-language, & Inventory API for Export Houses."

    def calculate_scenario(self, traffic, conv_rate, lead_value, hourly_rate, manual_hours, missed_lead_rate, speed_bonus_multiplier, business_name="Unknown", industry="General", language="english", is_realistic=False):
        traffic = max(0, traffic)
        
        # 1. LABOR SAVINGS (Annual)
        # The prompt formula: (Labor Hours * Hourly Wage * 12) * 0.80
        labor_savings_annual = (manual_hours * hourly_rate * 12) * 0.80
        
        # 2. RECOVERED REVENUE (Annual)
        # Missed Leads (Annual) = (Traffic * 12) * Missed Lead %
        # Formula: Missed Leads * Lead Value * (Conversion Rate * 1.2)
        multiplier = 1.2
        missed_leads_annual = (traffic * 12) * missed_lead_rate
        recovered_revenue_annual = missed_leads_annual * lead_value * ((conv_rate / 100) * multiplier)
        
        # 3. SAFETY BUFFER (20% variance)
        labor_savings_annual *= 0.80
        recovered_revenue_annual *= 0.80
        
        # 4. TOTAL GROSS BENEFIT (Annual)
        total_gross_benefit_annual = labor_savings_annual + recovered_revenue_annual
        
        assigned_monthly_cost, tier_name, tier_focus = self.get_pricing_tier(traffic)
        annual_cryvex_cost = assigned_monthly_cost * 12
        
        # 5. ROI FORMULA
        if annual_cryvex_cost > 0:
            roi_percentage = ((total_gross_benefit_annual - annual_cryvex_cost) / annual_cryvex_cost) * 100
        else:
            roi_percentage = 0
            
        is_negative = roi_percentage < 0
        
        if is_negative:
            roi_display = "0% (Break-even Analysis Required)"
            net_profit_annual = 0
            monthly_profit = 0
            payback_period_display = "N/A"
            break_even_days = "N/A"
        else:
            roi_display = f"{round(roi_percentage)}%"
            net_profit_annual = total_gross_benefit_annual - annual_cryvex_cost
            monthly_profit = net_profit_annual / 12
            
            # 6. PAYBACK PERIOD
            if total_gross_benefit_annual > 0:
                payback_months = annual_cryvex_cost / (total_gross_benefit_annual / 12)
                payback_period_display = f"{round(payback_months, 1)} Months"
                break_even_days = str(round(payback_months * 30, 1)) if payback_months >= 1 else "14-30"
            else:
                payback_period_display = "N/A"
                break_even_days = "N/A"
                
        # Efficiency
        efficiency = round((total_gross_benefit_annual / annual_cryvex_cost), 1) if annual_cryvex_cost > 0 else 0

        # Construct Dashboard Breakdown
        breakdown = {
            "section_a": {
                "title": "📊 ROI ANALYSIS REPORT",
                "how": f"<ul><li><b>Recommended Tier:</b> {tier_name}</li><li><b>Total Annual Savings (Hard Costs):</b> ₹{round(labor_savings_annual):,}</li><li><b>Projected Revenue Growth (Soft Costs):</b> ₹{round(recovered_revenue_annual):,}</li><li><b>Conservative Annual ROI:</b> {roi_display}</li><li><b>Payback Period:</b> {payback_period_display}</li></ul>"
            },
            "section_b": {
                "title": "🚀 SCALABILITY & SUSTAINABILITY",
                "how": f"<ul><li><b>Efficiency Score:</b> {efficiency}x multiplier based on 'Speed-to-Lead' response lift.</li><li><b>Green AI Impact:</b> Estimated carbon reduction of 1.2 thousands of lbs/month.</li></ul>"
            },
            "section_c": {
                "title": "🤖 THE CRYVEX EDGE",
                "how": f"<table><tr><th>Feature</th><th>Human Staff</th><th>Cryvex Digital Employee</th></tr><tr><td><b>Availability</b></td><td>40 hrs/week</td><td>168 hrs/week</td></tr><tr><td><b>Response</b></td><td>~15-30 mins</td><td>&lt; 2 seconds</td></tr><tr><td><b>Multitasking</b></td><td>Linear</td><td>Parallel</td></tr></table>"
            },
            "section_d": {
                "title": "💡 STRATEGIC ADVICE",
                "how": f"Based on your volume of {traffic} monthly visitors, {tier_name.capitalize()} is the ideal sweet spot to maximize your returns. It perfectly aligns with your need for {tier_focus.lower()}"
            }
        }
        
        monthly_gross_gain = total_gross_benefit_annual / 12
        return {
            "gross_benefit": round(monthly_gross_gain, 2),
            "net_profit": round(monthly_profit, 2),
            "annual_impact": round(net_profit_annual, 2),
            "efficiency_score": f"{efficiency}x Value",
            "break_even_days": break_even_days,
            "tier_name": tier_name,
            "subscription_cost": assigned_monthly_cost,
            "breakdown": breakdown
        }

    def analyze_scenarios(self, request: ROIRequest):
        """
        Runs the calculation through Conservative, Realistic, and Aggressive
        scenarios to provide a comprehensive analysis for B2B prospects.
        """
        # Baseline expectations
        scenarios = {
            "conservative": {"missed_lead_rate": 0.10, "speed_bonus_multiplier": 1.05}, # 10% recovered, +5% boost
            "realistic": {"missed_lead_rate": 0.25, "speed_bonus_multiplier": 1.21},    # 25% recovered, +21% boost
            "aggressive": {"missed_lead_rate": 0.40, "speed_bonus_multiplier": 1.35}     # 40% recovered, +35% boost
        }
        
        # Industry specific tailored assumptions for greater realism
        industry_multiplier = {
            "Real Estate": {"missed_lead_rate": 0.35, "speed_bonus_multiplier": 1.25}, # Highly speed-dependent
            "SaaS": {"missed_lead_rate": 0.20, "speed_bonus_multiplier": 1.15},        # Highly scaled, tech savvy
            "E-commerce": {"missed_lead_rate": 0.45, "speed_bonus_multiplier": 1.10},  # High volume leaking
            "Agency": {"missed_lead_rate": 0.20, "speed_bonus_multiplier": 1.30},      # High trust/velocity bonus
            "Finance": {"missed_lead_rate": 0.15, "speed_bonus_multiplier": 1.20},     # High value, moderate volume
        }
        
        if request.industry in industry_multiplier:
            scenarios["realistic"] = industry_multiplier[request.industry]
            
        results = {}
        for name, params in scenarios.items():
            results[name] = self.calculate_scenario(
                request.traffic, request.conv_rate, request.lead_value,
                request.hourly_rate, request.manual_hours,
                params["missed_lead_rate"], params["speed_bonus_multiplier"],
                request.business_name, request.industry, request.language,
                is_realistic=(name == "realistic")
            )
            
        return results

roi_engine = CryvexROIEngine()
