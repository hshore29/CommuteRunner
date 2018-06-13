// Set Map dimensions
var margin = {top: 8, bottom: 10, left: 8, right: 8},
    width = window.innerWidth - margin.left - margin.right,
    height = window.innerHeight - margin.top - margin.bottom,
    map_bounds = [[-75.9, 42], [-71.9, 40]],
    zoom_levels = [0.33, 0.5, 0.67, 1, 1.5, 2, 3],
    zoom_index = 3;

// D3 Variables defined during map creation
var color, stroke, projection, path, zoom, bounds,
    svg, zoombox, background, zips_layer, legs_layer;

// Set Color Scale Options
var D3_BLUE = ['#FFF', '#3182bd'];

// Setup basic D3 structures
function initializeMap() {
  // Define Scales
  color = d3.scale.category20();
  stroke = function (d, i) {
    return 1 / zoom_levels[zoom_index];
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
  if (s1 != s2) { legs_layer.selectAll("path").attr("stroke-width", stroke); }
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
      .attr("fill", (d, i) => color(d.properties.COUNTY))
      .attr("d", path)
      .on("mouseover", zipMouseOver);

  function zipMouseOver(d, i) {
    d3.select("#zip-name").text(d.properties.ZCTA5);
    d3.select("#zip-place").text(d.properties.PLACE || d.properties.COUNTY + ", " + d.properties.STATE);
  }
}

function colorZips(data, continuous, colors, max_domain) {
  if (!data) { return false; }
  if (continuous) {
    domain = d3.extent(Object.keys(data).map(k => data[k]));
    if (max_domain) { domain[1] = max_domain; }
    color = d3.scale.linear().domain(domain).range(colors);
  } else {
    color = d3.scale.category20();
  }
  zips_layer.selectAll("path").attr("fill", d => {
    val = data[d.properties.ZCTA5];
    if (val === undefined) {
      return "#FFF";
    } else if (val === null) {
      return "#CCC";
    } else {
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
    return color(val);
  });
}

// Add ZIP data layer
function addData(element, work_zip) {
  if (!element) {
    drawCommute(work_zip);
  } else if (element.startsWith('lookup')) {
    colorZipsMetadata(element);
  } else {
    d3.json("/data/" + element, function (data) {
      colorZips(data, true, D3_BLUE);
    });
  }
}

// Draw commute data
function drawCommute(work_zip) {
  d3.json("/commutes/times/" + work_zip, function (data) {
    colorZips(data, true, D3_BLUE, 5000);
  });
  d3.json("/commutes/lines/" + work_zip, function (data) {
    legs_layer.selectAll("path").remove();
    legs_layer.selectAll("path").data(data)
      .enter().append("path")
      .attr("fill", "none")
      .attr("stroke", d => d.colors[0] || "#AAA")
      .attr("stroke-width", stroke)
      .attr("stroke-dasharray", d => (d.mode == 'WALKING') ? "2,2" : null)
      .attr("d", d => path(d.geo));
  });
}