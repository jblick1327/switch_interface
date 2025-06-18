#stolen from somewhere online i forgot, basically a placeholder for now

import tkinter as tk

class VirtualKeyboard:
    """
    Class to create a virtual on-screen keyboard using Tkinter.

    Attributes:
    - root: tk.Tk
        The root window of the application.
    - entry: tk.Entry
        The entry widget where the keyboard inputs will be displayed.
    """

    def __init__(self):
        """
        Constructor to instantiate the VirtualKeyboard class.
        """

        # Creating the root window
        self.root = tk.Tk()
        self.root.title("Virtual Keyboard")

        # Creating the entry widget
        self.entry = tk.Entry(self.root)
        self.entry.pack()

        # Creating the buttons for the keyboard
        self.create_keyboard_buttons()

    def create_keyboard_buttons(self):
        """
        Creates the buttons for the virtual keyboard.
        """

        # List of button labels for the keyboard
        button_labels = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
            "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P",
            "A", "S", "D", "F", "G", "H", "J", "K", "L",
            "Z", "X", "C", "V", "B", "N", "M",
            "Space", "Backspace"
        ]

        # Function to handle button clicks
        def button_click(button_label):
            current_text = self.entry.get()

            if button_label == "Space":
                self.entry.insert(tk.END, " ")
            elif button_label == "Backspace":
                self.entry.delete(len(current_text) - 1)
            else:
                self.entry.insert(tk.END, button_label)

        # Creating the buttons
        for label in button_labels:
            button = tk.Button(self.root, text=label, width=5, command=lambda label=label: button_click(label))
            button.pack(side=tk.LEFT)

    def run(self):
        """
        Runs the virtual keyboard application.
        """
        self.root.mainloop()

# Creating an instance of the VirtualKeyboard class and running the application
keyboard = VirtualKeyboard()
keyboard.run()
                    