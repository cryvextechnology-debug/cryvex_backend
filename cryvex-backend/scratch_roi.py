import math

class CryvexROIEngineTest:
    def calculate_scenario(self, traffic, conv_rate, lead_value, hourly_rate, manual_hours, missed_lead_rate, speed_bonus_multiplier, business_name="Unknown", industry="General", language="english", is_realistic=False):
        traffic = max(0, traffic)
        
        # 1. LABOR SAVINGS (Annual)
        labor_savings_annual = (manual_hours * hourly_rate * 12) * 0.80
        
        # 2. RECOVERED REVENUE (Annual)
        # The prompt says (Conversion Rate * 1.2), and speed_bonus_multiplier is 1.05-1.35
        multiplier = 1.2
        missed_leads_annual = (traffic * 12) * missed_lead_rate
        recovered_revenue_annual = missed_leads_annual * lead_value * ((conv_rate / 100) * multiplier)
        
        # 3. SAFETY BUFFER (20% variance = 0.8 multiplier on savings)
        labor_savings_annual *= 0.80
        recovered_revenue_annual *= 0.80
        
        # TIER SELECTION
        if traffic < 150:
            assigned_monthly_cost = 1500
            tier_name = "STARTUP (Tier 1)"
            tier_focus = "24/7 FAQ & Lead Capture for local boutiques/shops."
        elif traffic <= 500:
            assigned_monthly_cost = 4900
            tier_name = "GROWTH (Tier 2)"
            tier_focus = "Lead Qualification & CRM Integration for mid-sized agencies."
        else:
            assigned_monthly_cost = 15000
            tier_name = "ENTERPRISE (Tier 3)"
            tier_focus = "Custom Training, Multi-language, & Inventory API for Export Houses."
            
        annual_cryvex_cost = assigned_monthly_cost * 12
        
        # TOTAL SAVINGS / GROWTH
        total_gross_benefit_annual = labor_savings_annual + recovered_revenue_annual
        
        # 4. ROI FORMULA
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
            
            if total_gross_benefit_annual > 0:
                payback_months = annual_cryvex_cost / (total_gross_benefit_annual / 12)
                payback_period_display = f"{round(payback_months, 1)} Months"
                break_even_days = str(round(payback_months * 30, 1)) if payback_months >= 1 else "14-30"
            else:
                payback_period_display = "N/A"
                break_even_days = "N/A"

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
                "how": f"Based on your volume of {traffic} monthly visitors, {tier_name.split(' ')[0]} is the ideal sweet spot to maximize your returns. It perfectly aligns with your need for {tier_focus.lower()}"
            }
        }
        
        return {
            "gross_benefit": round(total_gross_benefit_annual / 12, 2),
            "net_profit": round(monthly_profit, 2),
            "annual_impact": round(net_profit_annual, 2),
            "efficiency_score": f"{efficiency}x Value",
            "break_even_days": break_even_days,
            "tier_name": tier_name,
            "subscription_cost": assigned_monthly_cost,
            "breakdown": breakdown
        }

engine = CryvexROIEngineTest()
res = engine.calculate_scenario(traffic=200, conv_rate=5, lead_value=1000, hourly_rate=200, manual_hours=40, missed_lead_rate=0.25, speed_bonus_multiplier=1.21)
print(f"ROI Display: {res['breakdown']['section_a']['how']}")
print(f"Strategic Advice: {res['breakdown']['section_d']['how']}")
