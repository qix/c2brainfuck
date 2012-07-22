println("100 bottles of beer on the wall, 100 bottles of beer.");
println("Take one down and pass it around...");
for (l = '9'; l > '0'-1; l--) {
  for (s = '9'; s > '0'-1; s--) {
    if (l > '0') { print(l); }
    print(s);
    print(" bottles of beer on the wall, ");
    if (l > '0') { print(l, s); }
    else{ print(s); }
    println(" bottles of beer.");
    println("Take one down and pass it around...");
  }
}

