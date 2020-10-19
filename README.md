# note-renumber
Python code to renumber all endnotes in a Standard Ebooks project

Gets a list of epub content files in the order of the spine and runs through them locating all endnotes, renumbering from 1 onwards as it goes. Then rewrites the endnotes.xhtml file accordingly.

This version also processes endnotes within endnotes (placing embedded notes at the end of the endnotes list).

This project is in BETA. Use at your discretion and be sure to back up your project files!
