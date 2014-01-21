.PHONY: all clean

all: static/js/image-library.js

# Build static/js/image-library.js by running node third_party/rappar/rappar.js
# on each file in image_library/*.svg which generates a JSON object
# representing the SVG. Add all of these JSON objects to the imageLibrary
# object, using the filename (without extension) as the key like so:
#
# var imageLibrary = {
#     acorn: [...]
#     ,apple: [...]
#     ...
#     ,whale: [...]
# };
#
# Then concatenate that with the contents of image_library/image-library.js
#
static/js/image-library.js: image_library/*.svg image_library/image-library.js
	@echo "// Auto-generated file" > $@
	@echo "var imageLibrary = {" >> $@
	@$(foreach SVG,$(filter %.svg,$^), \
	    $(eval KEY=$(basename $(notdir $(SVG)))) \
	    echo $(KEY) ; \
	    if [ "x$(SVG)" != "x$<" ]; then /bin/echo -n ","; fi >> $@ ; \
	    /bin/echo -n "$(KEY):" >> $@ ; \
	    node third_party/rappar/rappar.js $(SVG) >> $@ ; \
	)
	@echo "};" >> $@
	@echo "" >> $@
	@cat image_library/image-library.js >> $@

clean:
	rm static/js/image-library.js
