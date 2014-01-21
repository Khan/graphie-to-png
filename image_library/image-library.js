// Custom exception that graphie-to-png catches and shows to the user
// If the user specifies an invalid image name, show a list of the valid ones
function UnknownImageException(name) {
    this.name = "Unknown image '" + name + "'. Valid images";
    var message = "\n\n";
    _.each(_.keys(imageLibrary).sort(), function(key) {
        message += "  " + key + "\n";
    });
    this.message = message;
}


function image(imageName, center, size) {
    image_data = imageLibrary[imageName];
    if (image_data == null) {
        throw new UnknownImageException(imageName);
    }
    var raphael = KhanUtil.currentGraph.raphael;
    var scale = KhanUtil.currentGraph.scale;
    var scalePoint = KhanUtil.currentGraph.scalePoint;
    set = raphael.set();
    _.each(image_data, function(obj, n) {
        var el;
        if (obj.type === "ellipse") {
            el = raphael.ellipse(obj.cx, obj.cy, obj.rx, obj.ry);
        } else if (obj.type === "circle") {
            el = raphael.ellipse(obj.cx, obj.cy, obj.r, obj.r);
        } else if (obj.type === "path") {
            el = raphael.path(obj.path);
        } else {
            console.error("Don't know how to handle element: " + obj.type);
            console.log(obj);
        }
        el.attr(obj);

        // TODO(eater): UGLY HACK! Raphael doesn't support radial gradients
        //              for any shapes other than circles and ellipses since
        //              such gradients only work in SVG, not VML. This tricks
        //              it into applying it anyway by lying about the element
        //              type by setting el.type to circle before applying the
        //              radial gradient fill. :\
        if (el.type === "path" && obj.fill && obj.fill[0] === "r") {
            el.type = "circle";
            el.attr({fill: obj.fill});
            el.type = "path";  // and no one will be the wiser...
        }

        // Translate Raphael 2.1 transforms into Raphael 1.5.2
        // translations and rotations
        if (obj.transform) {
            var m = obj.transform.match(/t([\-\d\.]+),([\-\d\.]+)/);
            if (m) {
                el.translate(m[1] + obj.cx, m[2] + obj.cy);
            }
            m = obj.transform.match(/r([\-\d\.]+),([\-\d\.]+),([\-\d\.]+)/);
            if (m) {
                el.rotate(m[1], m[2] + obj.cx, m[3] + obj.cy);
            }
        }
        set.push(el);
    });

    // Scale everything to the graphie size the user asked for
    var bbox = set.getBBox();
    set.translate(-bbox.x, -bbox.y);
    var scalefactor = (size * scale[0]) / Math.max(bbox.width, bbox.height);
    _.each(set, function(el) {
        // Manually scale the centers of any rotations
        if (typeof el.rotate() === "string") {
            var rotation = el.rotate().split(" ");
            el.rotate(rotation[0], rotation[1] * scalefactor,
                      rotation[2] * scalefactor);
        }
        // Manually scale stroke widths
        if (el.attr("stroke-width")) {
            el.attr("stroke-width", el.attr("stroke-width") * scalefactor);
        }
    });
    set.scale(scalefactor, scalefactor, 0, 0);
    set.translate(scalePoint(center)[0] - (scalefactor * bbox.width) / 2,
                  scalePoint(center)[1] - (scalefactor * bbox.height) / 2);
    return set;
}
