<?php
namespace Jobe;

/** Compile a student translation unit without linking or executing it. */
class CompilecppTask extends CppTask
{
    protected function compilerCommand()
    {
        return 'g++ -std=c++17';
    }

    public function compile()
    {
        $this->executableFileName = 'answer.o';
        $flags = array_map('escapeshellarg', $this->getParam('compileargs'));
        $cmd = $this->compilerCommand() . ' ' . implode(' ', $flags) . ' -c ' .
            escapeshellarg(basename($this->sourceFileName)) . ' -o answer.o';
        list($output, $this->cmpinfo) = $this->runInSandbox($cmd);
    }

    public function execute()
    {
        // Jobe calls execute after successful compilation; never run student code.
        $this->result = LanguageTask::RESULT_SUCCESS;
    }
}
