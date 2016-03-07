#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Adapted from elements of https://github.com/petercollingridge/SVG-Optimiser
import traceback

import lxml.etree
import svg.path
import collections
import re


def get_tag(element):
    """Get the tag name from an element

    In SVGs, `element.tag` is preceded by the namespace, so it looks like

        {http://www.w3.org/2000/svg}clipPath

    This retrieves the 'clipPath' part
    """
    return element.tag.split('}')[1]


def remove_element(element):
    element.getparent().remove(element)


def _cleanup_paths(tree):
    """Cleans up badly formatted paths in an SVG

    Many of the paths in the produced SVGs have large numbers of decimal
    places, which makes them large. Using the svg.path library, we parse the
    whole path and then spit the paths back out. The svg.path library rounds
    the points to an appropriate number of decimal places for us.
    """
    for element in tree.iter():
        tag = get_tag(element)

        if tag == "path":
            try:
                path = svg.path.parse_path(element.get("d"))
                # TODO(emily): Figure out a way to specify the number of
                # decimal places we want here.
                element.set("d", path.d())
            except:
                # Sometimes, svg.path fails to re-generate the path if it's
                # strange. We ignore this and leave the original path.
                continue


def _remove_desc(tree):
    """Remove the 'Created with Raphaël' description in the generated SVGs"""
    for element in tree.iter():
        tag = get_tag(element)

        if tag == "desc":
            remove_element(element)


STYLES_TO_REMOVE = frozenset(["-webkit-tap-highlight-color"])


def _cleanup_styles(tree):
    """Remove some of the styles that graphie automatically adds to the SVG

    Almost all of the elements in the produced SVG have a

        -webkit-tap-highlight-color: rgba(0, 0, 0, 0)

    in their inline styles. Here, we parse out the styles from the elements and
    remove that specific one.
    """
    for element in tree.iter():
        if "style" in element.keys():
            # Parse the original styles
            styles = [
                tuple(style.strip().split(':'))
                for style in element.attrib["style"].split(';')
                if len(style.strip()) > 0]

            # Remove ones we don't like
            cleaned_styles = [
                s for s in styles
                if s[0].strip() not in STYLES_TO_REMOVE]

            if len(cleaned_styles) == 0:
                # Remove the style attribute entirely if there are no more
                # styles
                del element.attrib["style"]
            else:
                # Otherwise re-generate the style string
                style_string = ';'.join(':'.join(s) for s in cleaned_styles)
                element.attrib["style"] = style_string


# Regex for matching clip-path urls
clip_path_url_regex = re.compile(r'url\(\#([^\)]+)\)')


def _cleanup_clip_paths(tree):
    """Remove duplicate clip paths, and shorten names

    Every time an element with a clip path is added in Raphaël, a new clipPath
    element is created with a unique ID to go along with it. This creates two
    problems: there are a lot of duplicate clip paths, and the unique ids that
    are generated are very long (like 'r-13302e1165e04ceea0c6420803f630ab'),
    both increasing the size of the SVG.

    To fix this, we first remove duplicate clip paths, and then we shorten the
    remaining names to 'clip-%d` for some unique number.
    """
    clip_paths = collections.defaultdict(list)
    to_remove = []
    clip_number = 1

    for element in tree.iter():
        tag = get_tag(element)

        # We only handle clipPaths with a single 'rect' child for now
        if tag == "clipPath" and len(element.getchildren()) == 1:
            child = element.getchildren()[0]

            if get_tag(child) == "rect":
                element_id = element.get('id')
                # TODO(emily): We don't do any rounding here, and just compare
                # string-to-string. Maybe do rounding of some sort?
                clip_def = (child.get('x'),
                            child.get('y'),
                            child.get('height'),
                            child.get('width'),
                            child.get('transform'))

                if clip_def in clip_paths:
                    # If we've already seen the same clip path, remove the
                    # element. We can't actually remove the elements here or
                    # the iterator gets messed up, so we add it to a list to
                    # remove later
                    to_remove.append(element)
                else:
                    # If we haven't seen the clip path, we generate a new
                    # unique name, and set the current clip path's id to it
                    new_element_id = "clip-%d" % clip_number
                    clip_number += 1
                    element.attrib["id"] = new_element_id
                    # We put the new id at the beginning of the list
                    clip_paths[clip_def].append(new_element_id)

                # Store a list of the ids associated with the same clip path
                clip_paths[clip_def].append(element_id)

    for element in to_remove:
        remove_element(element)

    clip_urls = {}

    # Generate a mapping from old ids to remaining ids
    for urls in clip_paths.itervalues():
        # The new url is the first thing in the list
        new_url = urls[0]

        for url in urls[1:]:
            clip_urls[url] = new_url

    # Replace instances of the old ids to the new ones
    for element in tree.iter():
        if "clip-path" in element.keys():
            path = element.get("clip-path")

            match = clip_path_url_regex.match(path)
            if match:
                url = match.group(1)

                if url in clip_urls:
                    element.attrib["clip-path"] = (
                        "url(#" + clip_urls[url] + ")")


def cleanup_svg(svgdata):
    """Run all of the cleanup functions on an svg file

    Read in an SVG file as a string, decode it using lxml, run all of the
    cleanup functions on it, and re-encode it"""
    try:
        tree = lxml.etree.fromstring(svgdata)

        _remove_desc(tree)
        _cleanup_paths(tree)
        _cleanup_styles(tree)
        _cleanup_clip_paths(tree)

        return lxml.etree.tostring(tree)
    except Exception, e:
        print e
        traceback.print_exc()

