<?php
namespace Jobe;

// All student compilation is performed through Jobe's compilation sandbox.
class Catch2cppTask extends CppTask
{
    protected $timings = array();
    protected function answerLanguage()
    {
        return 'cpp';
    }

    public static function getVersionCommand()
    {
        return array('cat /opt/catch2/VERSION', '/([0-9.]+)/');
    }

    public function compile()
    {
        $src = basename($this->sourceFileName);
        $this->executableFileName = $src . '.exe';
        $cmd = '/usr/local/bin/letto-catch2-compile ' .
            escapeshellarg($this->answerLanguage()) . ' ' .
            escapeshellarg($src) . ' ' . escapeshellarg($this->executableFileName);
        $flags = ' flags ' . escapeshellarg(json_encode($this->getParam('compileargs')));
        $started = hrtime(true);
        list($output, $this->cmpinfo) = $this->runInSandbox($cmd . ' prepare' . $flags);
        $this->timings = json_decode($output, true) ?: array();
        $key = $this->timings['test_cache_key'] ?? null;
        unset($this->timings['test_cache_key']);
        $this->timings['test_cache_hit'] = false;
        $lock = false;
        $cached = null;
        try {
            if (!$this->cmpinfo && is_string($key) && preg_match('/^[a-f0-9]{64}$/D', $key)) {
                $directory = '/var/cache/jobe/catch2';
                $cached = $directory . '/' . $key . '.o';
                $lock = @fopen($directory . '/' . $key . '.lock', 'c');
                if ($lock && flock($lock, LOCK_EX)) {
                    if (is_file($cached) && @copy($cached, 'catch2-tests.o')) {
                        $this->timings['test_cache_hit'] = true;
                    }
                } else {
                    $cached = null; // Cache unavailable: compilation still works.
                }
            }
            if (!$this->cmpinfo) {
                $hit = $this->timings['test_cache_hit'];
                list($output, $this->cmpinfo) = $this->runInSandbox($cmd . ' finish' . ($hit ? ' hit' : '') . $flags);
                $this->timings = array_merge($this->timings, json_decode($output, true) ?: array());
                if ($hit && $this->cmpinfo) {
                    // A doubtful cached object must never prevent a fresh build.
                    $retryStarted = hrtime(true);
                    list($output, $this->cmpinfo) = $this->runInSandbox($cmd . ' finish' . $flags);
                    $this->timings = array_merge($this->timings, json_decode($output, true) ?: array());
                    $this->timings['test_cache_retry_wall_seconds'] = (hrtime(true) - $retryStarted) / 1e9;
                    $this->timings['test_cache_hit'] = false;
                    $hit = false;
                }
                if (!$hit && $cached && !$this->cmpinfo && is_file('catch2-tests.o')) {
                    // Publish before student execution, atomically and as www-data.
                    $temporary = @tempnam(dirname($cached), 'building-');
                    if ($temporary !== false) {
                        if (@copy('catch2-tests.o', $temporary)) {
                            @chmod($temporary, 0644);
                            if (!@rename($temporary, $cached)) {
                                @unlink($temporary);
                            }
                        } else {
                            unlink($temporary);
                        }
                    }
                }
            }
        } finally {
            if ($lock) {
                flock($lock, LOCK_UN);
                fclose($lock);
            }
        }
        $this->timings['compile_sandbox_wall_seconds'] = (hrtime(true) - $started) / 1e9;
    }

    public function execute()
    {
        $started = hrtime(true);
        parent::execute();
        $this->timings['execute_sandbox_wall_seconds'] = (hrtime(true) - $started) / 1e9;
        if (preg_match('/__catch2_execution__(\{[^\n]+\})\n/', $this->stdout, $match)) {
            $execution = json_decode($match[1], true);
            if (is_array($execution)) {
                $this->timings = array_merge($this->timings, $execution);
            }
        }
    }

    public function resultObject()
    {
        $result = parent::resultObject();
        return new Catch2TimedResult($result, $this->timings);
    }
}

class Catch2TimedResult extends ResultObject
{
    public array $timings;

    public function __construct($result, $timings)
    {
        parent::__construct($result->run_id, $result->outcome, $result->cmpinfo,
            $result->stdout, $result->stderr);
        $this->timings = $timings;
    }
}
