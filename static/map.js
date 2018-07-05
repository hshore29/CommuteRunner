// Set Map dimensions
var margin = {top: 8, bottom: 10, left: 8, right: 8},
    width = window.innerWidth - margin.left - margin.right,
    height = window.innerHeight - margin.top - margin.bottom,
    map_bounds = [[-75.9, 42], [-71.9, 40]],
    zoom_levels = [0.33, 0.5, 0.67, 1, 1.5, 2, 3],
    zoom_index = 3;

// D3 Variables defined during map creation
var color, stroke, dashes, projection, path, zoom, bounds,
    svg, zoombox, background, zips_layer, path_layer, legs_layer, dots_layer;

// Set Color Scale Options
var D3_BLUE = ['#FFF', '#3182bd'];

// Set number format options
function pick_format(key) {
  switch (key) {
    case 'num':
      return d3.format(',f');
    case 'dec':
      return d3.format(',.1f');
    case 'pct':
      return d3.format(',.1%');
    case 'min':
      f = d3.format(',.1f');
      return s => f(s) + ' min';
    default:
      return s => s;
  }
}

// Setup basic D3 structures
function initializeMap() {
  // Define Scales
  stroke = function (d, i) {
    return 1 / zoom_levels[zoom_index];
  }
  dashes = function (d, i) {
    if (d.mode.startsWith('WALKING')) {
      dash = 2 / zoom_levels[zoom_index];
      return dash + ',' + dash;
    } else {
      return null
    }
  }

  projection = d3.geo.albers()
    .center([0, 40.7743])
    .rotate([73.971, 0])
    .translate([width/2, height/2])
    .scale(65000);

  path = d3.geo.path()
    .projection(projection);

  // Define view bounding box
  var bbox_rect = {
    "type": "LineString",
    "coordinates": [
      map_bounds[0], [map_bounds[1][0], map_bounds[0][1]],
      map_bounds[1], [map_bounds[0][0], map_bounds[1][1]],
      map_bounds[0]
    ]
  };
  bounds = [projection(map_bounds[0]), projection(map_bounds[1])];

  // Create SVG & G layers
  svg = d3.select("body").append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g");

  zoombox = svg.append("g");

  background = zoombox.append("g").attr("class", "background-layer");
  zips_layer = zoombox.append("g").attr("class", "zips-layer");
  dots_layer = zoombox.append("g").attr("class", "dots-layer");
  path_layer = zoombox.append("g").attr("class", "path-layer");
  legs_layer = zoombox.append("g").attr("class", "legs-layer");

  zoom = d3.behavior.zoom()
    .on("zoom", panned);
  svg.call(zoom);

  // Draw background
  background.append("path")
    .attr("fill", "white")
    .attr("d", path(bbox_rect));
}

// Zoom functions
function zoomed(trans) {
  // Update scale
  s1 = zoom.scale();
  s2 = zoom_levels[zoom_index];
  zoom.scale(s2);
  
  // Update translation
  trans[0] = d3.min([d3.max([trans[0] + width*(s1 - s2)/2, -bounds[1][0]*s2 + width]), -bounds[0][0]*s2]);
  trans[1] = d3.min([d3.max([trans[1] + height*(s1 - s2)/2, -bounds[1][1]*s2 + height]), -bounds[0][1]*s2]);
  zoom.translate(trans);
  
  // Update zoombox
  if (s1 != s2) {
    path_layer.selectAll("path").attr("stroke-width", stroke);
    legs_layer.selectAll("path").attr("stroke-width", stroke);
    legs_layer.selectAll("path").attr("stroke-dasharray", dashes);
  }
  zoombox.attr("transform", "translate(" + trans + ")scale(" + s2 + ")");
}

function panned() {
  if (d3.event.scale == zoom_levels[zoom_index]) {
    zoomed(d3.event.translate);
  }
}

function zoomInOut(dir) {
  // Shift levels, check if at limit
  $(".zoom-button").removeClass("disabled");
  if (dir == '+') {
    zoom_index = d3.min([zoom_index + 1, zoom_levels.length - 1]);
    if (zoom_index == zoom_levels.length - 1) {
      $("[data-zoom='+']").addClass("disabled");
    }
  } else {
    zoom_index = d3.max([zoom_index - 1, 0]);
    if (zoom_index == 0) {
      $("[data-zoom='-']").addClass("disabled");
    }
  }
  zoomed(zoom.translate());
}

// Draw Map function
function drawMap(data) {
  zips_layer.selectAll("path")
    .data(topojson.feature(data, data.objects.zcta).features)
    .enter().append("path")
      .attr("class", "zip")
      .attr("d", path)
      .on("mouseover", zipMouseOver);
  colorZipsMetadata('lookup:COUNTY');

  function zipMouseOver(d, i) {
    d3.select("#zip-name").text(d.properties.ZCTA5);
    d3.select("#zip-place").text(d.properties.PLACE || d.properties.COUNTY + ", " + d.properties.STATE);
    d3.select("#zip-data").text(d.properties.data_label || "");
  }
}

function drawDots(data) {
  dots_layer.selectAll("circle")
    .data(data)
    .enter().append("circle")
      .attr("cx", d => projection([(d.custom || d.centroid || d.google).lng, (d.custom || d.centroid || d.google).lat])[0])
      .attr("cy", d => projection([(d.custom || d.centroid || d.google).lng, (d.custom || d.centroid || d.google).lat])[1])
      .attr("r", 2)
      .attr("fill", D3_BLUE[1])
      .attr("data-zcta", d => d._id);
}

function drawRoutes(data) {
  path_layer.selectAll("path").data(data.features)
    .enter().append("path")
    .attr("fill", "none")
    .attr("stroke", d => d.properties.color)
    .attr("stroke-width", stroke)
    .attr("d", path);
}

function colorZips(data, continuous, format, colors, max_domain) {
  if (!data) { return false; }
  format = pick_format(format);
  if (continuous) {
    domain = d3.extent(Object.keys(data).map(k => data[k]));
    if (max_domain) { domain[1] = max_domain; }
    color = d3.scale.linear().domain(domain).range(colors);
  } else {
    color = d3.scale.category20();
  }
  zips_layer.selectAll("path").attr("fill", d => {
    val = data[d.properties.ZCTA5];
    d.properties.data = val;
    if (val === undefined) {
      d.properties.data_label = null;
      return "#FFF";
    } else if (val === null) {
      d.properties.data_label = 'None';
      return "#CCC";
    } else {
      d.properties.data_label = format(val);
      return color(val);
    }
  });
}

function colorZipsMetadata(lookup) {
  color = d3.scale.category20();
  lookup = lookup.split(':');
  zips_layer.selectAll("path").attr("fill", d => {
    val = d.properties[lookup[1]];
    val = (lookup.length == 3) ? val.slice(0, lookup[2]) : val;
    d.properties.data_label = val;
    return color(val);
  });
}

// Add ZIP data layer
function addData(element, work_zip, format) {
  $(".summary-box").hide();
  if (!element) {
    drawCommute(work_zip);
  } else if (element.startsWith('lookup')) {
    colorZipsMetadata(element);
  } else {
    d3.json("/data/" + element, function (data) {
      colorZips(data, true, format, D3_BLUE);
    });
  }
}

// Draw commute data
function drawCommute(work_zip) {
  d3.json("/commutes/times/" + work_zip, function (data) {
    colorZips(data.zips, true, "min", D3_BLUE, 60);
    $("#summary-data").text(pick_format('min')(data.total));
    $("#summary-zip").text(work_zip);
    $(".summary-box").show();
  });
  d3.json("/commutes/lines/" + work_zip, function (data) {
    legs_layer.selectAll("path").remove();
    legs_layer.selectAll("path").data(data)
      .enter().append("path")
      .attr("fill", "none")
      .attr("stroke", d => d.colors[0] || "#AAA")
      .attr("stroke-width", stroke)
      .attr("stroke-dasharray", dashes)
      .attr("opacity", d => opacity(d.weight))
      .attr("d", d => path(d.geo));
  });
}