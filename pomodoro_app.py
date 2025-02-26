import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
import json
import os
import platform
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import subprocess

@dataclass
class TimerTechnique:
    name: str
    work_time: int  # in minutes
    break_time: int  # in minutes
    long_break_time: int = 15  # in minutes
    cycles_before_long_break: int = 4
    description: str = ""

class PomodoroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pomodoro Timer")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        
        # Set app icon for macOS
        if platform.system() == "Darwin":  # macOS
            self.root.iconbitmap("tomato.icns")  # You'll need to create this icon file
        
        # Variables
        self.timer_running = False
        self.timer_paused = False
        self.current_timer = None
        self.remaining_time = 0
        self.current_phase = "work"  # "work" or "break" or "long_break"
        self.completed_cycles = 0
        
        # Load techniques from file or create default
        self.techniques = self.load_techniques()
        self.current_technique = self.techniques[0]
        
        # Create GUI
        self.create_widgets()
        
        # Center window
        self.center_window()
    
    def load_techniques(self) -> List[TimerTechnique]:
        """Load timer techniques from file or create defaults if file doesn't exist."""
        config_dir = self.get_config_dir()
        config_file = os.path.join(config_dir, "techniques.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    techniques_data = json.load(f)
                
                techniques = []
                for t_data in techniques_data:
                    techniques.append(TimerTechnique(
                        name=t_data["name"],
                        work_time=t_data["work_time"],
                        break_time=t_data["break_time"],
                        long_break_time=t_data.get("long_break_time", 15),
                        cycles_before_long_break=t_data.get("cycles_before_long_break", 4),
                        description=t_data.get("description", "")
                    ))
                return techniques
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load techniques: {str(e)}")
        
        # Default techniques
        return [
            TimerTechnique(
                name="Classic Pomodoro",
                work_time=25,
                break_time=5,
                description="The classic Pomodoro technique with 25-minute work sessions and 5-minute breaks."
            ),
            TimerTechnique(
                name="Long Focus",
                work_time=50,
                break_time=10,
                description="Longer focus sessions with 50-minute work periods and 10-minute breaks."
            ),
            TimerTechnique(
                name="Short Burst",
                work_time=15,
                break_time=3,
                description="Short bursts of intense focus with 15-minute work sessions and 3-minute breaks."
            )
        ]
    
    def save_techniques(self):
        """Save timer techniques to file."""
        config_dir = self.get_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, "techniques.json")
        
        techniques_data = []
        for technique in self.techniques:
            techniques_data.append({
                "name": technique.name,
                "work_time": technique.work_time,
                "break_time": technique.break_time,
                "long_break_time": technique.long_break_time,
                "cycles_before_long_break": technique.cycles_before_long_break,
                "description": technique.description
            })
        
        try:
            with open(config_file, 'w') as f:
                json.dump(techniques_data, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save techniques: {str(e)}")
    
    def get_config_dir(self) -> str:
        """Get the configuration directory based on the platform."""
        if platform.system() == "Darwin":  # macOS
            return os.path.expanduser("~/Library/Application Support/PomodoroTimer")
        else:
            return os.path.expanduser("~/.pomodoro_timer")
    
    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    
    def create_widgets(self):
        """Create all GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Timer technique selection
        ttk.Label(main_frame, text="Technique:").pack(pady=(0, 5), anchor=tk.W)
        
        technique_frame = ttk.Frame(main_frame)
        technique_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.technique_var = tk.StringVar(value=self.techniques[0].name)
        technique_dropdown = ttk.Combobox(
            technique_frame, 
            textvariable=self.technique_var,
            values=[t.name for t in self.techniques],
            state="readonly",
            width=25
        )
        technique_dropdown.pack(side=tk.LEFT)
        technique_dropdown.bind("<<ComboboxSelected>>", self.on_technique_changed)
        
        ttk.Button(technique_frame, text="Edit", command=self.edit_techniques).pack(side=tk.LEFT, padx=5)
        ttk.Button(technique_frame, text="Add", command=self.add_technique).pack(side=tk.LEFT)
        
        # Description label
        self.description_var = tk.StringVar(value=self.techniques[0].description)
        description_label = ttk.Label(
            main_frame, 
            textvariable=self.description_var,
            wraplength=360
        )
        description_label.pack(fill=tk.X, pady=(0, 15))
        
        # Timer display
        timer_frame = ttk.Frame(main_frame)
        timer_frame.pack(pady=10)
        
        self.time_display = ttk.Label(
            timer_frame, 
            text="25:00",
            font=("Helvetica", 48)
        )
        self.time_display.pack()
        
        # Phase indicator
        self.phase_var = tk.StringVar(value="Ready to start")
        phase_label = ttk.Label(
            timer_frame,
            textvariable=self.phase_var,
            font=("Helvetica", 14)
        )
        phase_label.pack(pady=(0, 10))
        
        # Progress indicators
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Cycle indicator
        self.cycle_var = tk.StringVar(value="Cycle: 0/4")
        cycle_label = ttk.Label(
            progress_frame,
            textvariable=self.cycle_var
        )
        cycle_label.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            orient="horizontal",
            length=360,
            mode="determinate"
        )
        self.progress.pack(fill=tk.X, pady=(0, 15))
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(pady=10)
        
        self.start_button = ttk.Button(
            control_frame,
            text="Start",
            command=self.start_timer,
            width=10
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.pause_button = ttk.Button(
            control_frame,
            text="Pause",
            command=self.pause_timer,
            width=10,
            state=tk.DISABLED
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        self.reset_button = ttk.Button(
            control_frame,
            text="Reset",
            command=self.reset_timer,
            width=10,
            state=tk.DISABLED
        )
        self.reset_button.pack(side=tk.LEFT, padx=5)
        
        # Settings section
        settings_frame = ttk.LabelFrame(main_frame, text="Quick Settings")
        settings_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Work time adjustment
        work_frame = ttk.Frame(settings_frame)
        work_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(work_frame, text="Work Time (min):").pack(side=tk.LEFT)
        
        self.work_time_var = tk.IntVar(value=self.current_technique.work_time)
        work_spinbox = ttk.Spinbox(
            work_frame,
            from_=1,
            to=120,
            textvariable=self.work_time_var,
            width=5,
            command=self.on_setting_changed
        )
        work_spinbox.pack(side=tk.RIGHT)
        
        # Break time adjustment
        break_frame = ttk.Frame(settings_frame)
        break_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(break_frame, text="Break Time (min):").pack(side=tk.LEFT)
        
        self.break_time_var = tk.IntVar(value=self.current_technique.break_time)
        break_spinbox = ttk.Spinbox(
            break_frame,
            from_=1,
            to=60,
            textvariable=self.break_time_var,
            width=5,
            command=self.on_setting_changed
        )
        break_spinbox.pack(side=tk.RIGHT)
        
        # Apply settings button
        ttk.Button(
            settings_frame,
            text="Apply Settings",
            command=self.apply_settings
        ).pack(pady=5)
        
        # Update the display
        self.update_display()
    
    def on_technique_changed(self, event):
        """Handle technique selection change."""
        selected_name = self.technique_var.get()
        
        for technique in self.techniques:
            if technique.name == selected_name:
                self.current_technique = technique
                self.description_var.set(technique.description)
                self.work_time_var.set(technique.work_time)
                self.break_time_var.set(technique.break_time)
                self.update_display()
                self.cycle_var.set(f"Cycle: 0/{technique.cycles_before_long_break}")
                break
    
    def on_setting_changed(self):
        """Handle when a setting value is changed."""
        # This method is called when spinbox values change
        # We don't update the technique immediately to allow users to change multiple settings at once
        pass
    
    def apply_settings(self):
        """Apply the current settings to the selected technique."""
        work_time = self.work_time_var.get()
        break_time = self.break_time_var.get()
        
        # Update the current technique
        self.current_technique.work_time = work_time
        self.current_technique.break_time = break_time
        
        # Save to file
        self.save_techniques()
        
        # Update display
        self.update_display()
        
        messagebox.showinfo("Settings Applied", "Your settings have been applied and saved.")
    
    def edit_techniques(self):
        """Open a dialog to edit all techniques."""
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Techniques")
        edit_window.geometry("500x400")
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # Create scrollable frame
        main_frame = ttk.Frame(edit_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add techniques to edit
        technique_frames = []
        for i, technique in enumerate(self.techniques):
            frame = ttk.LabelFrame(scrollable_frame, text=f"Technique {i+1}")
            frame.pack(fill=tk.X, expand=True, pady=5, padx=5)
            
            # Name field
            name_frame = ttk.Frame(frame)
            name_frame.pack(fill=tk.X, pady=2)
            ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT)
            name_var = tk.StringVar(value=technique.name)
            ttk.Entry(name_frame, textvariable=name_var).pack(side=tk.RIGHT, fill=tk.X, expand=True)
            
            # Work time
            work_frame = ttk.Frame(frame)
            work_frame.pack(fill=tk.X, pady=2)
            ttk.Label(work_frame, text="Work Time (min):").pack(side=tk.LEFT)
            work_var = tk.IntVar(value=technique.work_time)
            ttk.Spinbox(work_frame, from_=1, to=120, textvariable=work_var, width=5).pack(side=tk.RIGHT)
            
            # Break time
            break_frame = ttk.Frame(frame)
            break_frame.pack(fill=tk.X, pady=2)
            ttk.Label(break_frame, text="Break Time (min):").pack(side=tk.LEFT)
            break_var = tk.IntVar(value=technique.break_time)
            ttk.Spinbox(break_frame, from_=1, to=60, textvariable=break_var, width=5).pack(side=tk.RIGHT)
            
            # Long break time
            long_break_frame = ttk.Frame(frame)
            long_break_frame.pack(fill=tk.X, pady=2)
            ttk.Label(long_break_frame, text="Long Break Time (min):").pack(side=tk.LEFT)
            long_break_var = tk.IntVar(value=technique.long_break_time)
            ttk.Spinbox(long_break_frame, from_=1, to=60, textvariable=long_break_var, width=5).pack(side=tk.RIGHT)
            
            # Cycles before long break
            cycles_frame = ttk.Frame(frame)
            cycles_frame.pack(fill=tk.X, pady=2)
            ttk.Label(cycles_frame, text="Cycles Before Long Break:").pack(side=tk.LEFT)
            cycles_var = tk.IntVar(value=technique.cycles_before_long_break)
            ttk.Spinbox(cycles_frame, from_=1, to=10, textvariable=cycles_var, width=5).pack(side=tk.RIGHT)
            
            # Description
            desc_frame = ttk.Frame(frame)
            desc_frame.pack(fill=tk.X, pady=2)
            ttk.Label(desc_frame, text="Description:").pack(anchor=tk.W)
            desc_var = tk.StringVar(value=technique.description)
            ttk.Entry(desc_frame, textvariable=desc_var).pack(fill=tk.X, expand=True)
            
            # Delete button
            delete_button = ttk.Button(
                frame, 
                text="Delete", 
                command=lambda idx=i: self.delete_technique_frame(idx, technique_frames)
            )
            delete_button.pack(pady=5)
            
            # Store references to variables and the frame
            technique_frames.append({
                "frame": frame,
                "name_var": name_var,
                "work_var": work_var,
                "break_var": break_var,
                "long_break_var": long_break_var,
                "cycles_var": cycles_var,
                "desc_var": desc_var,
                "deleted": False
            })
        
        # Buttons
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            button_frame, 
            text="Save Changes",
            command=lambda: self.save_technique_changes(technique_frames, edit_window)
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Cancel",
            command=edit_window.destroy
        ).pack(side=tk.RIGHT, padx=5)
    
    def delete_technique_frame(self, idx, technique_frames):
        """Mark a technique frame as deleted."""
        if len([f for f in technique_frames if not f["deleted"]]) <= 1:
            messagebox.showerror("Error", "You must have at least one technique.")
            return
        
        technique_frames[idx]["deleted"] = True
        technique_frames[idx]["frame"].pack_forget()
    
    def save_technique_changes(self, technique_frames, window):
        """Save changes to techniques."""
        updated_techniques = []
        
        for frame_data in technique_frames:
            if frame_data["deleted"]:
                continue
            
            # Create updated technique
            technique = TimerTechnique(
                name=frame_data["name_var"].get(),
                work_time=frame_data["work_var"].get(),
                break_time=frame_data["break_var"].get(),
                long_break_time=frame_data["long_break_var"].get(),
                cycles_before_long_break=frame_data["cycles_var"].get(),
                description=frame_data["desc_var"].get()
            )
            
            updated_techniques.append(technique)
        
        # Update techniques
        self.techniques = updated_techniques
        self.save_techniques()
        
        # Update dropdown and current technique
        self.technique_var.set(self.techniques[0].name)
        self.current_technique = self.techniques[0]
        
        # Update UI
        technique_names = [t.name for t in self.techniques]
        technique_dropdown = self.root.nametowidget(self.root.winfo_children()[0].winfo_children()[2].winfo_children()[0])
        technique_dropdown['values'] = technique_names
        
        self.description_var.set(self.current_technique.description)
        self.work_time_var.set(self.current_technique.work_time)
        self.break_time_var.set(self.current_technique.break_time)
        self.update_display()
        
        # Close window
        window.destroy()
        
        messagebox.showinfo("Success", "Techniques have been updated successfully.")
    
    def add_technique(self):
        """Add a new technique."""
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New Technique")
        add_window.geometry("400x300")
        add_window.transient(self.root)
        add_window.grab_set()
        
        # Create form
        main_frame = ttk.Frame(add_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Name field
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT)
        name_var = tk.StringVar(value="New Technique")
        ttk.Entry(name_frame, textvariable=name_var).pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Work time
        work_frame = ttk.Frame(main_frame)
        work_frame.pack(fill=tk.X, pady=5)
        ttk.Label(work_frame, text="Work Time (min):").pack(side=tk.LEFT)
        work_var = tk.IntVar(value=25)
        ttk.Spinbox(work_frame, from_=1, to=120, textvariable=work_var, width=5).pack(side=tk.RIGHT)
        
        # Break time
        break_frame = ttk.Frame(main_frame)
        break_frame.pack(fill=tk.X, pady=5)
        ttk.Label(break_frame, text="Break Time (min):").pack(side=tk.LEFT)
        break_var = tk.IntVar(value=5)
        ttk.Spinbox(break_frame, from_=1, to=60, textvariable=break_var, width=5).pack(side=tk.RIGHT)
        
        # Long break time
        long_break_frame = ttk.Frame(main_frame)
        long_break_frame.pack(fill=tk.X, pady=5)
        ttk.Label(long_break_frame, text="Long Break Time (min):").pack(side=tk.LEFT)
        long_break_var = tk.IntVar(value=15)
        ttk.Spinbox(long_break_frame, from_=1, to=60, textvariable=long_break_var, width=5).pack(side=tk.RIGHT)
        
        # Cycles before long break
        cycles_frame = ttk.Frame(main_frame)
        cycles_frame.pack(fill=tk.X, pady=5)
        ttk.Label(cycles_frame, text="Cycles Before Long Break:").pack(side=tk.LEFT)
        cycles_var = tk.IntVar(value=4)
        ttk.Spinbox(cycles_frame, from_=1, to=10, textvariable=cycles_var, width=5).pack(side=tk.RIGHT)
        
        # Description
        desc_frame = ttk.Frame(main_frame)
        desc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(desc_frame, text="Description:").pack(anchor=tk.W)
        desc_var = tk.StringVar(value="")
        ttk.Entry(desc_frame, textvariable=desc_var).pack(fill=tk.X, expand=True)
        
        # Buttons
        button_frame = ttk.Frame(add_window)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            button_frame, 
            text="Add Technique",
            command=lambda: self.save_new_technique(
                name_var.get(),
                work_var.get(),
                break_var.get(),
                long_break_var.get(),
                cycles_var.get(),
                desc_var.get(),
                add_window
            )
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Cancel",
            command=add_window.destroy
        ).pack(side=tk.RIGHT, padx=5)
    
    def save_new_technique(self, name, work_time, break_time, long_break_time, cycles, description, window):
        """Save a new technique."""
        # Create new technique
        technique = TimerTechnique(
            name=name,
            work_time=work_time,
            break_time=break_time,
            long_break_time=long_break_time,
            cycles_before_long_break=cycles,
            description=description
        )
        
        # Add to list
        self.techniques.append(technique)
        self.save_techniques()
        
        # Update dropdown
        technique_names = [t.name for t in self.techniques]
        technique_dropdown = self.root.nametowidget(self.root.winfo_children()[0].winfo_children()[2].winfo_children()[0])
        technique_dropdown['values'] = technique_names
        
        # Close window
        window.destroy()
        
        messagebox.showinfo("Success", f"New technique '{name}' has been added successfully.")
    
    def update_display(self):
        """Update the time display based on the current technique and phase."""
        if self.timer_running and not self.timer_paused:
            # Display remaining time if timer is running
            minutes, seconds = divmod(self.remaining_time, 60)
            self.time_display.config(text=f"{minutes:02d}:{seconds:02d}")
            
            # Update progress bar
            if self.current_phase == "work":
                total_seconds = self.current_technique.work_time * 60
            elif self.current_phase == "break":
                total_seconds = self.current_technique.break_time * 60
            else:  # long_break
                total_seconds = self.current_technique.long_break_time * 60
            
            progress_value = ((total_seconds - self.remaining_time) / total_seconds) * 100
            self.progress['value'] = progress_value
        else:
            # Display work time when not running
            minutes = self.current_technique.work_time
            self.time_display.config(text=f"{minutes:02d}:00")
            self.progress['value'] = 0
    
    def start_timer(self):
        """Start the timer."""
        if self.timer_running and self.timer_paused:
            # Resume from pause
            self.timer_paused = False
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL, text="Pause")
        else:
            # Start new timer
            self.timer_running = True
            self.timer_paused = False
            
            # Set initial phase and time
            # Always start with work time when pressing start initially
            self.current_phase = "work"
            self.remaining_time = self.current_technique.work_time * 60
            self.phase_var.set("Work Time")
            
            # Start the timer thread
            self.current_timer = threading.Thread(target=self.run_timer)
            self.current_timer.daemon = True
            self.current_timer.start()
            
            # Update UI
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.NORMAL)
    
    def pause_timer(self):
        """Pause the timer."""
        if self.timer_running and not self.timer_paused:
            self.timer_paused = True
            self.pause_button.config(text="Resume")
            self.start_button.config(state=tk.NORMAL)
        else:
            self.timer_paused = False
            self.pause_button.config(text="Pause")
            self.start_button.config(state=tk.DISABLED)
    
    def reset_timer(self):
        """Reset the timer."""
        self.timer_running = False
        self.timer_paused = False
        self.current_phase = "ready"
        self.completed_cycles = 0
        self.phase_var.set("Ready to start")
        self.cycle_var.set(f"Cycle: 0/{self.current_technique.cycles_before_long_break}")
        
        # Update UI
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="Pause")
        self.reset_button.config(state=tk.DISABLED)
        
        # Reset display
        self.update_display()
    
    def run_timer(self):
        """Run the timer in a separate thread."""
        while self.timer_running and self.remaining_time > 0:
            if not self.timer_paused:
                # Decrement time
                self.remaining_time -= 1
                
                # Update display (must use thread-safe method)
                self.root.after(0, self.update_display)
                
                # Sleep for 1 second
                time.sleep(1)
            else:
                # When paused, just sleep briefly to prevent CPU hogging
                time.sleep(0.1)
        
        if self.timer_running:  # Only proceed if not reset
            # Timer complete, move to next phase
            self.root.after(0, self.handle_timer_complete)
    
    def handle_timer_complete(self):
        """Handle completion of a timer phase."""
        # Show notification
        self.show_notification()
        
        # Update phase
        if self.current_phase == "work":
            self.completed_cycles += 1
            
            if self.completed_cycles % self.current_technique.cycles_before_long_break == 0:
                # Time for a long break
                self.current_phase = "long_break"
                self.remaining_time = self.current_technique.long_break_time * 60
                self.phase_var.set("Long Break")
            else:
                # Regular break
                self.current_phase = "break"
                self.remaining_time = self.current_technique.break_time * 60
                self.phase_var.set("Break Time")
        else:
            # After any break, go back to work
            self.current_phase = "work"
            self.remaining_time = self.current_technique.work_time * 60
            self.phase_var.set("Work Time")
        
        # Update cycle indicator
        self.cycle_var.set(f"Cycle: {self.completed_cycles}/{self.current_technique.cycles_before_long_break}")
        
        # Start the timer again
        self.current_timer = threading.Thread(target=self.run_timer)
        self.current_timer.daemon = True
        self.current_timer.start()
    
    def show_notification(self):
        """Show a notification when a timer phase completes."""
        title = "Pomodoro Timer"
        
        if self.current_phase == "work":
            message = "Work period complete! Time for a break."
        elif self.current_phase == "break":
            message = "Break time complete! Back to work."
        else:  # long_break
            message = "Long break complete! Time to get back to work."
        
        # Display notification based on platform
        if platform.system() == "Darwin":  # macOS
            # Use AppleScript to display notification
            try:
                subprocess.run([
                    "osascript", 
                    "-e", 
                    f'display notification "{message}" with title "{title}"'
                ])
            except Exception as e:
                print(f"Error showing notification: {e}")
        else:
            # Fallback to Tkinter messagebox
            messagebox.showinfo(title, message)

def create_executable():
    """Create an executable file for macOS."""
    print("Creating executable for macOS...")
    print("Note: To create a proper macOS app, you'll need to use PyInstaller or py2app.")
    print("")
    print("Example using PyInstaller:")
    print("1. Install PyInstaller: pip install pyinstaller")
    print("2. Run: pyinstaller --onefile --windowed --icon=tomato.icns pomodoro_app.py")
    print("")
    print("Example using py2app:")
    print("1. Install py2app: pip install py2app")
    print("2. Create setup.py with appropriate configuration")
    print("3. Run: python setup.py py2app")

def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = PomodoroApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()