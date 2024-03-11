export var pixel_to_light = 1

export function render(index) {
  if(index == pixel_to_light){
    rgb(1,1,1)
  } else{
    rgb(0,0,0)
  }
}