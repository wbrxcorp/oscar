extern crate docopt;
//extern crate cpython;
extern crate rustc_serialize;
extern crate regex;
#[macro_use] extern crate lazy_static;
extern crate ruroonga;

//use cpython::{Python, PyDict, PyResult};

static USAGE: &'static str = "
Usage:
    wb hoge <hoge-fuga>...
    wb <other-cmd> [<other-cmd-args>...]
";

#[derive(RustcDecodable, Debug)]
struct Args {
    cmd_hoge: bool,
    arg_hoge_fuga: Vec<String>
}

pub fn main() {
    let args: Args = docopt::Docopt::new(USAGE).and_then(|d| d.decode()).unwrap_or_else(|e| e.exit());
    if args.cmd_hoge {
        use ruroonga as groonga;
        //let libgroonga = groonga::LibGroonga::new();
        println!("Hello in Ruroonga with Groonga: {}", groonga::Command::groonga_version());
        //println!("hoge: {:?}", args.arg_hoge_fuga);
    }
}
