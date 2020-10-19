#!/usr/bin/env python3
"""
routine which renumbers all endnotes in content order
"""
import argparse
import os
from bs4 import BeautifulSoup, Tag
from se.formatting import format_xhtml


class ListNote:
	"""
	Class to hold information on endnotes
	"""
	number = 0
	anchor = ""
	contents = []  # the strings and tags inside an <li> element
	back_link = ""
	source_file = ""
	matched = False


def get_content_files(opf: BeautifulSoup) -> list:
	"""
	Reads the spine from content.opf to obtain a list of content files, in the order wanted for the ToC.
	:param opf: Beautiful Soup object of the content.opf file
	:return: list of content files in the wanted order
	"""
	itemrefs = opf.find_all("itemref")
	ret_list = []
	for itemref in itemrefs:
		ret_list.append(itemref["idref"])
	return ret_list


def gethtml(file_path: str) -> str:
	"""
	reads an xhtml file and returns the text
	:param file_path: path to the xhtml file to process
	:return: text of xhtml file
	"""
	try:
		fileobject = open(file_path, 'r', encoding='utf-8')
	except IOError:
		print('Could not open ' + file_path)
		return ''
	text = fileobject.read()
	fileobject.close()
	return text


def extract_anchor(href: str) -> str:
	"""
	Extracts the anchor from a URL
	:param href: should be like: "../text/endnotes.xhtml#note-1"
	:return: just the part after the hash, eg "note-1"
	"""
	hash_position = href.find("#") + 1  # we want the characters AFTER the hash
	if hash_position > 0:
		return href[hash_position:]
	else:
		return ""


# global variable, unfortunately
notes_changed = 0

def process_file(text_path: str, file_name: str, endnotes: list, de_orphan: bool, current_note_number: int) -> int:
	"""
	Reads a content file, locates and processes the endnotes,
	accumulating info on them in a global list, and returns the next note number
	:param text_path: path to the text files in the project
	:param file_name: the name of the file being processed eg chapter-1.xhtml
	:param endnotes: list of notes we are building
	:param de_orphan: remove reference in text if no matching endnote
	:param current_note_number: the current note number we are allocating
	:return: the next note number to use
	"""
	global notes_changed
	file_path = os.path.join(text_path, file_name)
	xhtml = gethtml(file_path)
	soup = BeautifulSoup(xhtml, "lxml")
	links = soup.find_all("a")
	needs_rewrite = False
	for link in links:
		epub_type = link.get("epub:type") or ""
		if epub_type == "noteref":
			old_anchor = ""
			href = link.get("href") or ""
			if href:
				old_anchor = extract_anchor(href)
			new_anchor = "note-{:d}".format(current_note_number)
			if new_anchor != old_anchor:
				print("Changed " + old_anchor + " to " + new_anchor + " in " + file_path)
				notes_changed += 1
				# update the link in the soup object
				link["href"] = 'endnotes.xhtml#' + new_anchor
				link["id"] = 'noteref-{:d}'.format(current_note_number)
				link.string = str(current_note_number)
				needs_rewrite = True
			# now try to find this in endnotes
			matches = list(filter(lambda x: x.anchor == old_anchor, endnotes))
			if len(matches) == 0:
				print("Couldn't find endnote with anchor " + old_anchor)
				if de_orphan:
					print("Removing orphan note ref in text")
					link.clear()
					needs_rewrite = True
			elif len(matches) > 1:
				print("Duplicate anchors in endnotes file for anchor " + old_anchor)
			else:  # found a single match, which is what we want
				listnote = matches[0]
				listnote.number = current_note_number
				listnote.matched = True
				# we don't change the anchor or the back ref just yet
				listnote.source_file = file_name
			current_note_number += 1

	# if we need to write back the body text file
	if needs_rewrite:
		new_file = open(file_path, "w")
		new_file.write(format_xhtml(str(soup)))
		# new_file.write(str(soup))
		new_file.close()
	return current_note_number


def process_endnotes_file(endnotes: list, de_orphan: bool, current_note_number: int) -> int:
	"""
	Reads the endnotes in memory, looking for note links WITHIN the body of notes
	:param endnotes: list of notes we are building
	:param de_orphan: remove reference in text if no matching endnote
	:param current_note_number: the current note number we are allocating
	:return: the next note number to use
	"""
	global notes_changed
	for endnote in endnotes:
		for content in endnote.contents:
			if isinstance(content, Tag):
				links = content.find_all("a")
				for link in links:
					epub_type = link.get("epub:type") or ""
					if epub_type == "noteref":
						old_anchor = ""
						href = link.get("href") or ""
						if href:
							old_anchor = extract_anchor(href)
						new_anchor = "note-{:d}".format(current_note_number)
						if new_anchor != old_anchor:
							print("Changed " + old_anchor + " to " + new_anchor + " in endnotes.xhtml")
							notes_changed += 1
							# update the link in the soup object
							link["href"] = 'endnotes.xhtml#' + new_anchor
							link["id"] = 'noteref-{:d}'.format(current_note_number)
							link.string = str(current_note_number)
							needs_rewrite = True
							# now try to find this in existing endnotes
							matches = list(filter(lambda x: x.anchor == old_anchor, endnotes))
							if len(matches) == 0:
								print("Couldn't find endnote with anchor " + old_anchor)
								if de_orphan:
									print("Removing orphan note ref in text")
									link.clear()
									needs_rewrite = True
							elif len(matches) > 1:
								print("Duplicate anchors in endnotes file for anchor " + old_anchor)
							else:  # found a single match, which is what we want
								listnote = matches[0]
								listnote.number = current_note_number
								listnote.matched = True
								# we don't change the anchor or the back ref just yet
								listnote.source_file = "endnotes.xhtml"
								listnote.anchor = new_anchor
							current_note_number += 1
	return current_note_number


def get_notes(endnotes_soup: BeautifulSoup) -> list:
	"""
	gets the list of notes in the current endnotes.xhtml file
	:param endnotes_soup: the endnotes.xhtml file as a BS object
	:return: list of note objects
	"""
	ret_list = []
	ol: BeautifulSoup = endnotes_soup.find("ol")
	items = ol.find_all("li")
	# do something
	for item in items:
		note = ListNote()
		note.contents = []
		for content in item.contents:
			note.contents.append(content)
			if isinstance(content, Tag):
				links = content.find_all("a")
				for link in links:
					epub_type = link.get("epub:type") or ""
					if epub_type == "se:referrer" or epub_type == "backlink":
						href = link.get("href") or ""
						if href:
							note.back_link = href
		note.anchor = item.get("id") or ""

		ret_list.append(note)
	return ret_list


def recreate(textpath: str, notes_soup: BeautifulSoup, endnotes: list):
	"""
	rebuilds endnotes.xhtml in the correct (possibly new) order
	:param textpath: path to text folder in SE project
	:param notes_soup:
	:param endnotes:
	:return:
	"""
	ol = notes_soup.ol
	ol.clear()
	endnotes.sort(key=lambda enote: enote.number)
	for endnote in endnotes:
		if endnote.matched:
			li = notes_soup.new_tag("li")
			li["id"] = "note-" + str(endnote.number)
			li["epub:type"] = "endnote"
			for content in endnote.contents:
				if isinstance(content, Tag):
					links = content.find_all("a")
					for link in links:
						epub_type = link.get("epub:type") or ""
						if "se:referrer" in epub_type or "backlink" in epub_type:
							href = link.get("href") or ""
							if href:
								link["href"] = endnote.source_file + "#noteref-" + str(endnote.number)
				li.append(content)
			ol.append(li)
	new_file = open(os.path.join(textpath, "endnotes.xhtml"), "w")
	new_file.write(format_xhtml(str(notes_soup)))
	new_file.close()


# don't process these files
exclude_list = ["titlepage.xhtml", "colophon.xhtml", "uncopyright.xhtml", "imprint.xhtml", "halftitle.xhtml", "endnotes.xhtml"]


def main():
	global notes_changed
	parser = argparse.ArgumentParser(description="Renumber endnotes from beginning")
	parser.add_argument("-r", "--remove_orphans", action="store_true", help="remove notes in text if note is missing in endnotes.xhtml")
	parser.add_argument("directory", metavar="DIRECTORY", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	rootpath = args.directory
	opfpath = os.path.join(rootpath, 'src', 'epub', 'content.opf')
	textpath = os.path.join(rootpath, 'src', 'epub', 'text')
	notespath = os.path.join(rootpath, 'src', 'epub', 'text', 'endnotes.xhtml')

	if not os.path.exists(opfpath):
		print("Error: this does not seem to be a Standard Ebooks root directory")
		exit(-1)

	if not os.path.exists(notespath):
		print("Error: no endnotes file exists")
		exit(-1)

	if args.remove_orphans:
		de_orphan = True
	else:
		de_orphan = False

	xhtml = gethtml(notespath)
	notes_soup = BeautifulSoup(xhtml, "lxml")
	endnotes = get_notes(notes_soup)

	xhtml = gethtml(opfpath)
	soup = BeautifulSoup(xhtml, "lxml")
	file_list = get_content_files(soup)

	processed = 0
	current_num = 1
	for file_name in file_list:
		if file_name in exclude_list:
			continue
		print("Processing " + file_name)
		processed += 1
		current_num = process_file(textpath, file_name, endnotes, de_orphan, current_num)
		print("Endnotes processed so far: " + str(current_num - 1))  # we subtract 1 because process_file increments it after each note found
	# look inside endnotes.xhtml itself for notes to notes
	process_endnotes_file(endnotes, de_orphan, current_num)
	if processed == 0:
		print("No files processed. Did you update manifest and order the spine?")
	else:
		print("Found {:d} endnotes.".format(current_num - 1))
		if notes_changed > 0:
			print("Changed {:d} endnotes".format(notes_changed))
			# so we need to recreate the endnotes file
			recreate(textpath, notes_soup, endnotes)
		else:
			print("No changes made")


if __name__ == "__main__":
	main()
