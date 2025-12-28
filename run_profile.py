import cProfile
import main

if __name__ == "__main__":
    cProfile.run('main.main()', 'prof.prof')