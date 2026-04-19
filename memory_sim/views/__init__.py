"""View widgets composing the simulator window."""

from .control_panel import ControlPanel
from .memory_map import MemoryMap
from .step_controls import StepControls
from .step_log import StepLog
from .stats_panel import StatsPanel
from .educational import EducationalSection
from .comparison import ComparisonDialog
from .toast import ToastManager
from .fragmentation_chart import FragmentationChart
from .status_bar import StatusBar
from .command_palette import CommandPalette

__all__ = [
    "ControlPanel",
    "MemoryMap",
    "StepControls",
    "StepLog",
    "StatsPanel",
    "EducationalSection",
    "ComparisonDialog",
    "ToastManager",
    "FragmentationChart",
    "StatusBar",
    "CommandPalette",
]
