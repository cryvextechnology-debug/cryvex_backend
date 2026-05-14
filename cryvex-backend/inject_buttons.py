import os
import glob

# Search across all HTML files in frontend
html_files = glob.glob(r"c:\Users\Anandhu\.gemini\antigravity\scratch\cryvex-backend\frontend\*.html")

target_marker = """            <div class="calc-row" style="border:none; padding:0; margin:0;">
                <div><span style="display:block; font-weight:600; margin-bottom: 5px;">Recovered with Cryvex</span><span style="color: var(--text-muted); font-size: 0.9rem;">Predictive AI Intervention Model</span></div>
                <div class="calc-val" style="color: var(--accent);">+$112,500</div>
            </div>
        </div>"""

replacement_marker = """            <div class="calc-row" style="border:none; padding:0; margin:0;">
                <div><span style="display:block; font-weight:600; margin-bottom: 5px;">Recovered with Cryvex</span><span style="color: var(--text-muted); font-size: 0.9rem;">Predictive AI Intervention Model</span></div>
                <div class="calc-val" style="color: var(--accent);">+$112,500</div>
            </div>
        </div>
        <button class="cta-btn cta-primary action-btn-roi" onclick="runCalc(this)" style="margin-top: 2rem; background: var(--surface); color: white; border: 1px solid var(--primary);">Run Financial Simulation ⚡</button>"""

script_target = """        function simulateAction(actionName) {"""
script_replacement = """        function runCalc(btn) {
            simulateAction('calculated_roi');
            btn.style.background = '#10B981';
            btn.style.borderColor = '#34D399';
            btn.textContent = 'Simulating Return Ratio...';
        }

        function simulateAction(actionName) {"""


for file_path in html_files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "Run Financial Simulation" not in content:
        content = content.replace(target_marker, replacement_marker)
        
    if "function runCalc(btn)" not in content:
        content = content.replace(script_target, script_replacement)
        
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Updated {len(html_files)} files with ROI buttons!")
