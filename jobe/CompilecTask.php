<?php
namespace Jobe;

class CompilecTask extends CompilecppTask
{
    protected function compilerCommand()
    {
        return 'gcc -std=c17';
    }

    public function defaultFileName($sourcecode)
    {
        return 'answer.c';
    }
}
