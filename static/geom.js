function area(poly) {
  a = 0;
  for (var i = 0; i < poly.length - 1; i++) {
    a += (poly[i][0]*poly[i+1][1] - poly[i+1][0]*poly[i][1]);
  }
  return a/2;
}

function cent_x(poly) {
  cx = 0;
  for (var i = 0; i < poly.length - 1; i++) {
    cx += (poly[i][0] + poly[i+1][0])*(poly[i][0]*poly[i+1][1] - poly[i+1][0]*poly[i][1])
  }
  return cx / (6 * area(poly));
}

function cent_y(poly) {
  cx = 0;
  for (var i = 0; i < poly.length - 1; i++) {
    cx += (poly[i][1] + poly[i+1][1])*(poly[i][0]*poly[i+1][1] - poly[i+1][0]*poly[i][1])
  }
  return cx / (6 * area(poly));
}

function center(geometry) {
  if (geometry.type == 'Polygon') {
    return [cent_x(geometry.coordinates[0]), cent_y(geometry.coordinates[0])];
  }
  if (geometry.type == 'MultiPolygon') {
    var tot_a = 0,
        cy = 0,
        cx = 0;
    for (var i = 0; i < geometry.coordinates.length; i++) {
      a = area(geometry.coordinates[i][0]);
      cx += cent_x(geometry.coordinates[i][0]) * a;
      cy += cent_y(geometry.coordinates[i][0]) * a;
      tot_a += a;
    }
    return [cx / tot_a, cy / tot_a];
  }
}