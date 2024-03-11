export function render3D(index,x,y,z) {
    if(z != 0){
      rgb(0,0,0)
    }
    else if (x > 0.5) {
      rgb(1, 0, 0)
    }
    else {
      rgb(0,1,0)
    }
  }