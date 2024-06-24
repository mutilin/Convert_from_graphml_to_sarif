Чтобы указать, какую трассу визуализировать, необоходимо в функции parse_graphml указать нужный путь к трассе. Затем в строчку

with open('converter/package/testN/result.sarif', 'w') as sarif_file:

где вместо N, поставить номер нужного теста, который хотите запустить.\newline
Запускается скрипт командой:\\
make runcode.\\
Если хотите в качестве параметра передать спецификацию, необходимо в makefile поставить нужную спецификацию в следующем формате:\\
CHECK( init(main()), LTL(G ! call(func())) )\\
CHECK( init(main()), LTL(G valid-free) )\\
CHECK( init(main()), LTL(G valid-deref) )\\
CHECK( init(main()), LTL(G valid-memtrack) )\\
CHECK( init(main()), LTL(G valid-memcleanup) )\\
CHECK( init(main()), LTL(G ! overflow) )\\
CHECK( init(main()), LTL(G ! data-race) )\\
CHECK( init(main()), LTL(F end) )\\
