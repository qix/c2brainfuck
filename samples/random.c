for (k = 0; k < 20; k++) {
  hex = rand() % 16;
  if (hex > 9) {
    print('a'+hex-10);
  }else{
    print('0'+hex);
  }
}
