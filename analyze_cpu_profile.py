#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "matplotlib>=3.5.0",
#     "pandas>=1.3.0",
#     "rich>=12.0.0",
# ]
# ///

"""
CPU Profile Analyzer for Ice Application

Analyzes Apple's sample/spindump output to identify performance bottlenecks,
with special focus on event monitoring and high-frequency operations.
"""

import re
import sys
from collections import defaultdict, Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse

import pandas as pd
import matplotlib.pyplot as plt
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

@dataclass
class StackFrame:
    """Represents a single stack frame in the call graph"""
    samples: int
    function_name: str
    library: str
    address: str
    source_info: str = ""
    depth: int = 0

@dataclass
class CategoryStats:
    """Statistics for a category of functions"""
    total_samples: int
    functions: List[StackFrame]
    percentage: float

class CPUProfileAnalyzer:
    """Analyzes CPU profiling data from Apple's sample/spindump format"""
    
    def __init__(self, profile_file: Path):
        self.profile_file = profile_file
        self.console = Console()
        self.total_samples = 0
        self.frames: List[StackFrame] = []
        self.categories = {
            "Event Monitoring": [],
            "Ice Application": [],
            "UI/SwiftUI": [],
            "System Frameworks": [],
            "Memory Management": [],
            "Graphics/Display": [],
            "Other": []
        }
        
    def parse_profile(self) -> None:
        """Parse the sample file and extract stack frames"""
        self.console.print("[yellow]Reading CPU profile...[/yellow]")
        
        with open(self.profile_file, 'r') as f:
            content = f.read()
        
        # Extract total samples from header
        total_match = re.search(r'(\d+)\s+Thread_\d+:\s+Main Thread', content)
        if total_match:
            self.total_samples = int(total_match.group(1))
        
        # Parse call graph entries
        call_graph_pattern = r'^\s*(\+\s*)*([!:+|\s]*)(\d+)\s+(.+?)\s+\(in\s+(.+?)\)\s*\+\s*\d+\s*\[([^\]]+)\](?:\s+(.+?))?$'
        
        for line in content.split('\n'):
            if not line.strip() or line.startswith('Analysis of') or line.startswith('Process:'):
                continue
                
            match = re.match(call_graph_pattern, line)
            if match:
                depth = len(match.group(2)) if match.group(2) else 0
                samples = int(match.group(3))
                function_name = match.group(4).strip()
                library = match.group(5).strip()
                address = match.group(6).strip()
                source_info = match.group(7).strip() if match.group(7) else ""
                
                frame = StackFrame(
                    samples=samples,
                    function_name=function_name,
                    library=library,
                    address=address,
                    source_info=source_info,
                    depth=depth
                )
                
                self.frames.append(frame)
                self._categorize_frame(frame)
    
    def _categorize_frame(self, frame: StackFrame) -> None:
        """Categorize a stack frame based on function name and library"""
        func_lower = frame.function_name.lower()
        lib_lower = frame.library.lower()
        
        # Event monitoring patterns
        event_patterns = [
            'nsevent', 'event', 'monitor', 'mouse', 'scroll', 'hover',
            'nextevent', 'dispatch', 'pullevents', '_blockuntilnext',
            'receivenextevent', 'cgsdecode', 'slevent'
        ]
        
        if any(pattern in func_lower for pattern in event_patterns):
            self.categories["Event Monitoring"].append(frame)
        elif frame.library == "Ice":
            self.categories["Ice Application"].append(frame)
        elif any(ui in lib_lower for ui in ['swiftui', 'appkit', 'uikit']):
            self.categories["UI/SwiftUI"].append(frame)
        elif any(mem in func_lower for mem in ['alloc', 'malloc', 'free', 'retain', 'release']):
            self.categories["Memory Management"].append(frame)
        elif any(gfx in lib_lower for gfx in ['skylight', 'coregraphics', 'quartzcore']):
            self.categories["Graphics/Display"].append(frame)
        elif any(sys in lib_lower for sys in ['foundation', 'coredata', 'libsystem', 'libobjc']):
            self.categories["System Frameworks"].append(frame)
        else:
            self.categories["Other"].append(frame)
    
    def analyze_hotspots(self) -> Dict[str, CategoryStats]:
        """Analyze CPU hotspots by category"""
        stats = {}
        
        for category, frames in self.categories.items():
            total_samples = sum(frame.samples for frame in frames)
            percentage = (total_samples / self.total_samples * 100) if self.total_samples > 0 else 0
            
            # Sort frames by sample count
            sorted_frames = sorted(frames, key=lambda f: f.samples, reverse=True)
            
            stats[category] = CategoryStats(
                total_samples=total_samples,
                functions=sorted_frames[:10],  # Top 10
                percentage=percentage
            )
        
        return stats
    
    def find_ice_hotspots(self) -> List[StackFrame]:
        """Find top CPU consuming functions in Ice application"""
        ice_frames = [f for f in self.frames if f.library == "Ice"]
        return sorted(ice_frames, key=lambda f: f.samples, reverse=True)[:20]
    
    def analyze_event_monitoring(self) -> Dict[str, int]:
        """Analyze event monitoring overhead"""
        event_samples = defaultdict(int)
        
        for frame in self.frames:
            func_lower = frame.function_name.lower()
            if any(pattern in func_lower for pattern in ['event', 'monitor', 'mouse', 'scroll']):
                event_samples[frame.function_name] += frame.samples
        
        return dict(sorted(event_samples.items(), key=lambda x: x[1], reverse=True))
    
    def generate_insights(self, stats: Dict[str, CategoryStats]) -> List[str]:
        """Generate actionable insights based on analysis"""
        insights = []
        
        # Check event monitoring overhead
        event_stats = stats.get("Event Monitoring", CategoryStats(0, [], 0))
        if event_stats.percentage > 30:
            insights.append(
                f"🔥 HIGH: Event monitoring consuming {event_stats.percentage:.1f}% of CPU - "
                "Consider reducing global NSEvent monitor frequency or adding debouncing"
            )
        elif event_stats.percentage > 15:
            insights.append(
                f"⚠️ MEDIUM: Event monitoring consuming {event_stats.percentage:.1f}% of CPU - "
                "May benefit from optimization"
            )
        
        # Check Ice-specific overhead
        ice_stats = stats.get("Ice Application", CategoryStats(0, [], 0))
        if ice_stats.percentage > 20:
            insights.append(
                f"🔥 HIGH: Ice application code consuming {ice_stats.percentage:.1f}% of CPU - "
                "Review high-frequency operations and caching strategies"
            )
        
        # Check UI overhead
        ui_stats = stats.get("UI/SwiftUI", CategoryStats(0, [], 0))
        if ui_stats.percentage > 25:
            insights.append(
                f"⚠️ MEDIUM: UI/SwiftUI consuming {ui_stats.percentage:.1f}% of CPU - "
                "Consider reducing view updates and using lazy loading"
            )
        
        # Check graphics overhead
        gfx_stats = stats.get("Graphics/Display", CategoryStats(0, [], 0))
        if gfx_stats.percentage > 20:
            insights.append(
                f"⚠️ MEDIUM: Graphics/Display consuming {gfx_stats.percentage:.1f}% of CPU - "
                "Window server communication overhead detected"
            )
        
        if not insights:
            insights.append("✅ No major performance issues detected in this sample")
        
        return insights
    
    def create_visualization(self, stats: Dict[str, CategoryStats]) -> None:
        """Create CPU usage visualization"""
        categories = list(stats.keys())
        percentages = [stats[cat].percentage for cat in categories]
        
        plt.figure(figsize=(12, 8))
        
        # Create bar chart
        plt.subplot(2, 1, 1)
        bars = plt.bar(categories, percentages, color=['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57', '#ff9ff3', '#54a0ff'])
        plt.title('CPU Usage by Category', fontsize=16, fontweight='bold')
        plt.ylabel('CPU Usage (%)')
        plt.xticks(rotation=45, ha='right')
        
        # Add percentage labels on bars
        for bar, pct in zip(bars, percentages):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # Create pie chart for non-zero categories
        plt.subplot(2, 1, 2)
        non_zero_cats = [(cat, pct) for cat, pct in zip(categories, percentages) if pct > 0]
        if non_zero_cats:
            cats, pcts = zip(*non_zero_cats)
            plt.pie(pcts, labels=cats, autopct='%1.1f%%', startangle=90)
            plt.title('CPU Usage Distribution', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('cpu_profile_analysis.png', dpi=150, bbox_inches='tight')
        self.console.print(f"[green]Visualization saved as cpu_profile_analysis.png[/green]")
    
    def print_detailed_report(self, stats: Dict[str, CategoryStats]) -> None:
        """Print detailed analysis report"""
        self.console.print(Panel.fit("🔍 CPU Profile Analysis Report", style="bold blue"))
        
        # Summary table
        summary_table = Table(title="CPU Usage Summary")
        summary_table.add_column("Category", style="cyan", no_wrap=True)
        summary_table.add_column("Samples", justify="right", style="magenta")
        summary_table.add_column("Percentage", justify="right", style="green")
        summary_table.add_column("Top Function", style="yellow")
        
        for category, stat in sorted(stats.items(), key=lambda x: x[1].percentage, reverse=True):
            if stat.percentage > 0:
                top_func = stat.functions[0].function_name[:50] + "..." if stat.functions and len(stat.functions[0].function_name) > 50 else (stat.functions[0].function_name if stat.functions else "N/A")
                summary_table.add_row(
                    category,
                    str(stat.total_samples),
                    f"{stat.percentage:.2f}%",
                    top_func
                )
        
        self.console.print(summary_table)
        
        # Ice-specific hotspots
        ice_hotspots = self.find_ice_hotspots()
        if ice_hotspots:
            self.console.print("\n")
            ice_table = Table(title="🧊 Top Ice Application Hotspots")
            ice_table.add_column("Samples", justify="right", style="magenta")
            ice_table.add_column("Function", style="cyan")
            ice_table.add_column("Source", style="green")
            
            for frame in ice_hotspots[:10]:
                ice_table.add_row(
                    str(frame.samples),
                    frame.function_name,
                    frame.source_info or "Unknown"
                )
            
            self.console.print(ice_table)
        
        # Event monitoring analysis
        event_analysis = self.analyze_event_monitoring()
        if event_analysis:
            self.console.print("\n")
            event_table = Table(title="🖱️ Event Monitoring Overhead")
            event_table.add_column("Samples", justify="right", style="magenta")
            event_table.add_column("Event Function", style="yellow")
            
            for func, samples in list(event_analysis.items())[:10]:
                event_table.add_row(str(samples), func)
            
            self.console.print(event_table)
    
    def run_analysis(self) -> None:
        """Run complete CPU profile analysis"""
        self.parse_profile()
        stats = self.analyze_hotspots()
        insights = self.generate_insights(stats)
        
        self.console.print(f"\n[bold green]Total Samples:[/bold green] {self.total_samples}")
        self.console.print(f"[bold green]Unique Functions:[/bold green] {len(self.frames)}")
        
        self.print_detailed_report(stats)
        
        # Print insights
        self.console.print("\n")
        insights_panel = Panel("\n".join(insights), title="🎯 Actionable Insights", style="bold")
        self.console.print(insights_panel)
        
        # Create visualization
        self.create_visualization(stats)
        
        # Performance recommendations
        recommendations = [
            "1. Consider adding debouncing to global NSEvent monitors",
            "2. Profile Ice-specific functions with instruments for deeper analysis", 
            "3. Implement lazy loading for UI components that update frequently",
            "4. Cache expensive operations like image processing",
            "5. Use background queues for non-UI intensive operations"
        ]
        
        rec_panel = Panel("\n".join(recommendations), title="💡 Performance Recommendations", style="green")
        self.console.print(rec_panel)

def main():
    parser = argparse.ArgumentParser(description="Analyze Ice CPU profile for performance bottlenecks")
    parser.add_argument("profile_file", help="Path to the CPU sample file (e.g., Sample of Ice4.txt)")
    parser.add_argument("--output", "-o", help="Output directory for generated files", default=".")
    
    args = parser.parse_args()
    
    profile_path = Path(args.profile_file)
    if not profile_path.exists():
        print(f"Error: Profile file '{profile_path}' not found", file=sys.stderr)
        sys.exit(1)
    
    analyzer = CPUProfileAnalyzer(profile_path)
    analyzer.run_analysis()

if __name__ == "__main__":
    main()
