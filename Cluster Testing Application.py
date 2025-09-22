import tkinter as tk
from tkinter import filedialog, messagebox
from threading import Thread, Event
import cantools
import can
import can.interfaces.pcan
import time



class CANSignalSenderApp:
    def __init__(self, root):
        # Interface and bitrate configuration maps
        self.interface_channel_map = {
            "Peak CAN": ["pcan", "PCAN_USBBUS1"],
            "Kvaser CAN": ["kvaser", "0"],
            "Chuangxin USBCAN": ["canalystii", "0"],
            "Virtual CAN": ["virtual", "vcan0"]
        }

        self.bitrate_map = {
            "125 kbps": 125000,
            "250 kbps": 250000,
            "500 kbps": 500000,
            "1 Mbps": 1000000,
        }

        # CAN Configuration variables
        self.interface_selection = tk.StringVar(value="Select Interface")
        self.bitrate_selection = tk.StringVar(value="Select Bitrate")
        self.channel_selection = tk.StringVar(value="Select Channel")

        # Other variables
        self.db = None
        self.dbc_path = tk.StringVar()
        self.bus = None

        # Signal/UI state
        self.toggling = {}  # signal_name -> bool (on/off)
        self.signal_entries = {}  # signal_name -> Entry widget
        self.toggle_buttons = {}  # signal_name -> Button widget

        # Per-message worker model
        self.messages_by_id = {}  # frame_id -> cantools message
        self.signal_to_message_id = {}  # signal_name -> frame_id
        self.message_threads = {}  # frame_id -> Thread
        self.message_stop_events = {}  # frame_id -> Event
        self.message_current_values = {}  # frame_id -> {signal_name: current_physical_value}

        # Global cycle time (ms) for sends when signals are active
        self.cycle_time_ms = tk.IntVar(value=100)  # default 100 ms

        # Tkinter root and widgets
        self.root = root
        self.root.title("Cluster Testing Application")

        self.create_widgets()

    def create_widgets(self):
        # Load DBC File
        tk.Label(self.root, text="DBC File:", font=("Arial, 14")).grid(row=0, column=0, sticky="e", padx=10, pady=10)
        tk.Entry(self.root, textvariable=self.dbc_path, width=50, state="readonly", font=("Arial", 12)).grid(
            row=0, column=1, padx=10, pady=10
        )
        tk.Button(self.root, text="Load DBC", command=self.load_dbc, font=("Arial", 12), width=15).grid(
            row=0, column=2, padx=10, pady=10
        )

        # Interface Dropdown
        tk.Label(self.root, text="CAN Interface:", font=("Arial", 14)).grid(row=1, column=0, sticky="e", padx=10,
                                                                            pady=10)
        tk.OptionMenu(
            self.root, self.interface_selection, *self.interface_channel_map.keys()
        ).grid(row=1, column=1, sticky="w", padx=10, pady=10)

        # Bitrate Dropdown
        tk.Label(self.root, text="CAN Bitrate:", font=("Arial", 14)).grid(row=2, column=0, sticky="e", padx=10, pady=10)
        tk.OptionMenu(self.root, self.bitrate_selection, *self.bitrate_map.keys()).grid(
            row=2, column=1, sticky="w", padx=10, pady=10
        )

        # Start Interface Button
        self.start_button = tk.Button(
            self.root, text="Start Interface", command=self.start_interface, font=("Arial", 12)
        )
        self.start_button.grid(row=3, column=1, pady=10)

        # Toggle All controls
        all_controls = tk.Frame(self.root)
        all_controls.grid(row=3, column=2, sticky="w", padx=10)
        tk.Button(all_controls, text="Toggle All ON", command=self.toggle_all_on, font=("Arial", 11)).pack(side="left",
                                                                                                           padx=5)
        tk.Button(all_controls, text="Toggle All OFF", command=self.toggle_all_off, font=("Arial", 11)).pack(
            side="left", padx=5)

        # Cycle time radio buttons
        cycle_frame = tk.LabelFrame(self.root, text="Cycle Time", padx=10, pady=5, font=("Arial", 11, "bold"))
        cycle_frame.grid(row=3, column=0, sticky="w", padx=10)
        options_ms = [10, 20, 50, 100, 200, 500, 1000]
        for ms in options_ms:
            tk.Radiobutton(
                cycle_frame,
                text=f"{ms} ms",
                variable=self.cycle_time_ms,
                value=ms
            ).pack(side="left", padx=3)

        # Scrollable area for signals
        signal_frame_container = tk.Frame(self.root, width=900, height=450)
        signal_frame_container.grid(row=4, column=0, columnspan=3, pady=20, sticky="nsew")
        signal_frame_container.grid_propagate(False)

        # Scrollable canvas
        canvas = tk.Canvas(signal_frame_container, highlightthickness=0, bg="white")
        scrollbar = tk.Scrollbar(signal_frame_container, orient="vertical", command=canvas.yview)
        self.signal_frame = tk.Frame(canvas, bg="white")

        self.signal_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.signal_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind trackpad scrolling gestures
        def on_mouse_wheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

        # Bind scrolling gestures for Windows/Mac
        canvas.bind_all("<MouseWheel>", on_mouse_wheel)

        # Bind scrolling gestures for Linux
        canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def start_interface(self):
        """Initialize the CAN interface connection."""
        # Validate selections
        if self.interface_selection.get() == "Select Interface":
            messagebox.showerror("Error", "Select a CAN interface!")
            return
        if self.bitrate_selection.get() == "Select Bitrate":
            messagebox.showerror("Error", "Select a CAN bitrate!")
            return

        try:
            selected_interface_channel = self.interface_channel_map[self.interface_selection.get()]
            interface = selected_interface_channel[0]
            channel = selected_interface_channel[1]
            bitrate = self.bitrate_map[self.bitrate_selection.get()]

            # Create CAN bus connection
            self.bus = can.interface.Bus(interface=interface, channel=channel, bitrate=bitrate)
            messagebox.showinfo("Success", "CAN interface started successfully!")
            self.start_button.config(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start CAN interface: {str(e)}")

    def load_dbc(self):
        """Load signals from a DBC file and create toggleable buttons."""
        file_path = filedialog.askopenfilename(filetypes=[("DBC Files", "*.dbc")])
        if file_path:
            try:
                self.db = cantools.database.load_file(file_path)
                self.dbc_path.set(file_path)

                # Index messages by frame_id
                self.messages_by_id.clear()
                self.signal_to_message_id.clear()
                self._destroy_signal_buttons()

                for message in self.db.messages:
                    self.messages_by_id[message.frame_id] = message

                # Display the list of signals as toggleable rows
                self.create_signal_buttons()
                messagebox.showinfo("Success", f"DBC Loaded: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load DBC: {str(e)}")

    def _destroy_signal_buttons(self):
        if self.signal_frame is not None:
            for widget in self.signal_frame.winfo_children():
                widget.destroy()
        # Clear previous UI state
        self.signal_entries.clear()
        self.toggling.clear()
        self.toggle_buttons.clear()

    def _signal_limits_physical(self, sig):
        """
        Compute physical min/max for a signal.
        Uses DBC-provided limits if present; otherwise derives from bit length and signedness with scale/offset.
        """
        scale = sig.scale if sig.scale is not None else 1.0
        offset = sig.offset if sig.offset is not None else 0.0
        if sig.minimum is not None and sig.maximum is not None:
            return float(sig.minimum), float(sig.maximum)

        length = sig.length
        if sig.is_signed:
            raw_min = -(1 << (length - 1))
            raw_max = (1 << (length - 1)) - 1
        else:
            raw_min = 0
            raw_max = (1 << length) - 1

        phys_min = raw_min * scale + offset
        phys_max = raw_max * scale + offset
        # Ensure ordering
        if phys_min > phys_max:
            phys_min, phys_max = phys_max, phys_min
        return float(phys_min), float(phys_max)

    def _neutral_value(self, sig):
        """
        Choose a neutral 'off' physical value for a signal:
        - Prefer 0.0 clamped within physical range
        - If 0.0 outside range, fall back to physical minimum
        """
        phys_min, phys_max = self._signal_limits_physical(sig)
        neutral = 0.0
        if neutral < phys_min:
            neutral = phys_min
        if neutral > phys_max:
            neutral = phys_max
        return neutral

    def create_signal_buttons(self):
        """Create toggleable rows for each signal in the DBC."""
        for message in self.db.messages:
            for signal in message.signals:
                signal_name = signal.name
                phys_min, phys_max = self._signal_limits_physical(signal)

                # Map signal -> message (frame)
                self.signal_to_message_id[signal_name] = message.frame_id

                # Each signal row
                frame = tk.Frame(self.signal_frame)
                frame.pack(fill="x", pady=2)

                # Signal name and min/max (show as physical/decoded)
                tk.Label(frame, text=f"{signal_name} (Min: {phys_min:g}, Max: {phys_max:g})").pack(side="left", padx=5)

                # Entry box for signal value (decoded/physical units)
                value_entry = tk.Entry(frame, width=12, font=("Arial", 10))
                value_entry.pack(side="left", padx=5)
                # Default to auto-increment "A"
                value_entry.insert(0, "A")
                self.signal_entries[signal_name] = value_entry

                # Start/Stop toggle button
                self.toggling[signal_name] = False

                toggle_button = tk.Button(
                    frame,
                    text=f"Off: {signal_name}",
                    bg="lightgray",
                    relief="raised",
                    font=("Arial", 10, "bold")
                )
                toggle_button.config(
                    command=lambda s=signal_name, m=message, max_v=phys_max,
                                   entry=value_entry, btn=toggle_button: self.toggle_signal_with_custom_value(
                        s, m, max_v, entry, btn
                    )
                )
                toggle_button.pack(side="right", padx=5, pady=2)
                self.toggle_buttons[signal_name] = toggle_button

    def toggle_signal_with_custom_value(self, signal_name, message, phys_max, value_entry, button):
        """
        Toggle start/stop of a signal with custom value input via Entry and provide on/off feedback.
        Entry expects:
          - 'A' (case-insensitive) for auto-increment mode (default)
          - a numeric value for constant transmission (including 0)
        """
        if not self.bus:
            messagebox.showerror("Error", "Start the CAN interface first!")
            return

        if not self.toggling[signal_name]:
            # Validate entry; accept 'A' or a valid number
            raw = value_entry.get().strip()
            if raw.upper() != "A":
                try:
                    _ = float(raw)
                except ValueError:
                    messagebox.showerror("Error", f"Invalid value for {signal_name}. Use 'A' or a number.")
                    return

            # Turn ON
            self.toggling[signal_name] = True
            self._ensure_message_worker(message)
            button.config(text=f"On: {signal_name}", bg="green", relief="sunken")
        else:
            # Turn OFF
            self.toggling[signal_name] = False
            # Immediately send a single "final off" frame for this signal
            self._send_final_off_for_signal(message, signal_name)
            self._stop_message_worker_if_idle(message)
            button.config(text=f"Off: {signal_name}", bg="lightgray", relief="raised")

    def toggle_all_on(self):
        """Turn on all signals and start workers as needed."""
        if not self.bus:
            messagebox.showerror("Error", "Start the CAN interface first!")
            return
        # Ensure DBC loaded
        if not self.signal_entries:
            messagebox.showerror("Error", "Load a DBC first!")
            return

        # Validate values (set invalid to 'A')
        for name, entry in self.signal_entries.items():
            raw = entry.get().strip()
            if raw == "":
                entry.delete(0, tk.END)
                entry.insert(0, "A")
                raw = "A"
            if raw.upper() != "A":
                try:
                    _ = float(raw)
                except ValueError:
                    entry.delete(0, tk.END)
                    entry.insert(0, "A")

        # Turn all on and ensure workers
        for name in list(self.toggling.keys()):
            self.toggling[name] = True
            frame_id = self.signal_to_message_id.get(name)
            if frame_id is not None:
                msg = self.messages_by_id.get(frame_id)
                if msg is not None:
                    self._ensure_message_worker(msg)
            # Update buttons
            btn = self.toggle_buttons.get(name)
            if btn is not None:
                btn.config(text=f"On: {name}", bg="green", relief="sunken")

    def toggle_all_off(self):
        """Turn off all signals, send final off for each, and stop idle workers."""
        if not self.signal_entries:
            return

        # Set all off and send final-off per signal
        handled_msgs = set()
        for name in list(self.toggling.keys()):
            if self.toggling[name]:
                self.toggling[name] = False
                frame_id = self.signal_to_message_id.get(name)
                if frame_id is not None:
                    msg = self.messages_by_id.get(frame_id)
                    if msg is not None:
                        self._send_final_off_for_signal(msg, name)
                        handled_msgs.add(frame_id)
            # Update buttons
            btn = self.toggle_buttons.get(name)
            if btn is not None:
                btn.config(text=f"Off: {name}", bg="lightgray", relief="raised")

        # Stop workers if idle
        for frame_id in handled_msgs:
            msg = self.messages_by_id.get(frame_id)
            if msg is not None:
                self._stop_message_worker_if_idle(msg)

    def _ensure_message_worker(self, message):
        """Start a single worker thread for this message if not already running."""
        frame_id = message.frame_id
        if frame_id not in self.message_stop_events:
            self.message_stop_events[frame_id] = Event()
        stop_event = self.message_stop_events[frame_id]

        if frame_id not in self.message_threads or not self.message_threads[frame_id].is_alive():
            # Initialize per-message current values to signal minimums (physical)
            self.message_current_values[frame_id] = {
                sig.name: self._signal_limits_physical(sig)[0] for sig in message.signals
            }
            stop_event.clear()
            t = Thread(target=self._message_worker, args=(message,))
            t.daemon = True
            self.message_threads[frame_id] = t
            t.start()

    def _stop_message_worker_if_idle(self, message):
        """Stop the worker if no signals for this message are currently toggled on."""
        frame_id = message.frame_id
        any_active = any(self.toggling.get(sig.name, False) for sig in message.signals)
        if not any_active and frame_id in self.message_stop_events:
            self.message_stop_events[frame_id].set()
            if frame_id in self.message_threads:
                self.message_threads[frame_id].join(timeout=2)

    def _send_final_off_for_signal(self, message, signal_name):
        """
        Build and send a single frame for 'message' where only 'signal_name' is forced to its neutral (zero) value.
        Other signals keep their last known values to avoid disturbing them.
        """
        if not self.bus:
            return
        try:
            frame_id = message.frame_id
            # Start from last known values or physical mins if absent
            base_vals = dict(self.message_current_values.get(frame_id, {
                sig.name: self._signal_limits_physical(sig)[0] for sig in message.signals
            }))
            # Force the target signal to neutral
            target_sig = next((s for s in message.signals if s.name == signal_name), None)
            if target_sig is None:
                return
            base_vals[signal_name] = self._neutral_value(target_sig)

            encoded = message.encode(base_vals)
            msg = can.Message(
                arbitration_id=message.frame_id,
                data=encoded,
                is_extended_id=message.is_extended_frame
            )
            self.bus.send(msg)
            # Update cached values to reflect the off-send
            self.message_current_values[frame_id] = base_vals
        except Exception as e:
            messagebox.showerror("Error",
                                 f"Failed to send final off for {signal_name} (0x{message.frame_id:X}): {str(e)}")

    def _message_worker(self, message):
        """
        Single worker per message:
        - Entry boxes contain DECoded/physical values.
        - Each tick:
            - If a signal is toggled ON and entry == 'A' (case-insensitive): increment physical value by 1.0 until max, then stay at max.
            - If toggled ON and entry is numeric: clamp to [phys_min, phys_max] and use it directly (0 allowed).
            - If toggled OFF: force the signal to its neutral 'off' value (e.g., 0.0 clamped), so it no longer carries the last value.
        - Send at the globally selected cycle time.
        """
        frame_id = message.frame_id
        stop_event = self.message_stop_events[frame_id]
        current_values = self.message_current_values.get(frame_id) or {
            sig.name: self._signal_limits_physical(sig)[0] for sig in message.signals
        }

        # Precompute physical min/max per signal
        limits = {sig.name: self._signal_limits_physical(sig) for sig in message.signals}
        neutrals = {sig.name: self._neutral_value(sig) for sig in message.signals}

        while not stop_event.is_set():
            try:
                any_active = False

                for sig in message.signals:
                    name = sig.name
                    phys_min, phys_max = limits[name]
                    neutral = neutrals[name]
                    entry_widget = self.signal_entries.get(name)

                    if self.toggling.get(name, False):
                        any_active = True
                        # Read entry; 'A' means auto-increment
                        entry_text = entry_widget.get().strip() if entry_widget is not None else "A"
                        if entry_text.upper() == "A" or entry_text == "":
                            # Auto-increment by 1.0 physical unit up to max, then stay at max
                            val = current_values.get(name, phys_min)
                            if val < phys_max:
                                val = min(val + 1.0, phys_max)
                            else:
                                val = phys_max
                            current_values[name] = val
                        else:
                            # Use entry value directly, clamp within physical limits
                            try:
                                entry_val = float(entry_text)
                            except Exception:
                                entry_val = phys_min
                            if entry_val < phys_min:
                                entry_val = phys_min
                            if entry_val > phys_max:
                                entry_val = phys_max
                            current_values[name] = entry_val
                    else:
                        # OFF: explicitly set to neutral (do not keep the last value)
                        current_values[name] = neutral

                # Only send if at least one signal is active for this message
                if any_active:
                    encoded = message.encode(current_values)
                    msg = can.Message(
                        arbitration_id=message.frame_id,
                        data=encoded,
                        is_extended_id=message.is_extended_frame
                    )
                    self.bus.send(msg)

                # Respect global cycle time and remain responsive to stop
                interval = max(0.001, self.cycle_time_ms.get() / 1000.0)
                if stop_event.wait(interval):
                    break

            except Exception as e:
                messagebox.showerror("Error", f"Failed to send message 0x{message.frame_id:X}: {str(e)}")
                break

        # Persist last known values
        self.message_current_values[frame_id] = current_values


if __name__ == "__main__":
    root = tk.Tk()
    app = CANSignalSenderApp(root)
    root.mainloop()
