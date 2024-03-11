export var pixels_to_light = array(pixelCount);

export function render(index) {
  var p = pixels_to_light[index]
  if(p){
    rgb(1,1,1)
  } else {
  rgb(0,0,0)
  }
}
