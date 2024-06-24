Чтобы указать, какую трассу визуализировать, необоходимо в функции parse_graphml указать нужный путь к трассе. Затем в строчку

with open('converter/package/testN/result.sarif', 'w') as sarif_file:

где вместо N, поставить номер нужного теста, который хотите запустить.<br />
Запускается скрипт командой:<br />
make runcode.<br />
Если хотите в качестве параметра передать спецификацию, необходимо в makefile поставить нужную спецификацию в следующем формате:<br />
CHECK( init(main()), LTL(G ! call(func())) )<br />
CHECK( init(main()), LTL(G valid-free) )<br />
CHECK( init(main()), LTL(G valid-deref) )<br />
CHECK( init(main()), LTL(G valid-memtrack) )<br />
CHECK( init(main()), LTL(G valid-memcleanup) )<br />
CHECK( init(main()), LTL(G ! overflow) )<br />
CHECK( init(main()), LTL(G ! data-race) )<br />
CHECK( init(main()), LTL(F end) )
