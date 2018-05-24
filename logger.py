import time
import sys
import csv
from threading import Thread

class Logger(Thread):

    def __init__(self, job_spec, inst_drivers, log_out=sys.stdout):
        Thread.__init__(self)
        self.job = job_spec

        #log file name
        t = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        self.out_dir = "data_files\\"
        self.rawfilename = "p" + t + self.job["datafile_raw"]
        self.transfilename = "p" + t + self.job["datafile_trans"]
        self.op_names = self.job["logged_operations"]

        #todo load from inst spec
        self.min_cycle_time = 2
        # store and file setup
        self.raw_dict = {}
        self.trans_dict = {}
        self.store=[]
        self.file_setup()
        #instrument operations and v_timer instrument
        self.instruments = inst_drivers
        self.instruments['time'] = Timer()
        self.operations=[]
        self.setup_operations()

        self.count = 0

        self.paused = True
        self.stopped = False

    def run(self):
        print("starting")
        self.start_time = time.time()
        self.paused = False
        self.mainloop()

    def mainloop(self):
        while not self.stopped:
            while not self.paused:
                self.read_loop()
            time.sleep(1)
        sys.exit(1)

    def read_loop(self):
        ls_time = time.time()
        self.raw_dict = {}
        self.trans_dict = {}
        for inst, op in self.operations:
            self.read_instrument(inst,op)

        self.log_to_file()
        self.store.append((self.raw_dict,self.trans_dict))
        self.count += 1
        cycle_time = time.time()-ls_time
        ttnc = self.min_cycle_time-cycle_time
        if ttnc > 0:
            time.sleep(ttnc)

    def read_instrument(self,inst_id,operation_id):
        inst = self.instruments.get(inst_id)
        result = inst.read_instrument(operation_id)
        self.raw_dict["{}.{}".format(inst_id, operation_id)] = result[0]
        self.trans_dict["{}.{}".format(inst_id, operation_id)] = result[1]

    def file_setup(self):
        datafile = self.out_dir + self.rawfilename
        with open(datafile, "w+") as outfile:
            for k, v in self.job.items():
                if k not in ["instruments", "logged_operations"]:
                    outfile.write(k + ": " + str(v) + "\n")
            writer = csv.writer(outfile, self.job["logged_operations"], lineterminator='\n')
            writer.writerow(self.op_names)
        datafile = self.out_dir + self.transfilename
        with open(datafile, "w+") as outfile:
            for k, v in self.job.items():
                if k not in ["instruments", "logged_operations"]:
                    outfile.write(k + ": " + str(v) + "\n")
            writer = csv.writer(outfile, self.job["logged_operations"], lineterminator='\n')
            writer.writerow(self.op_names)

    def setup_operations(self):
        for operation in self.op_names:
            inst_id,op_id = operation.split('.')
            if inst_id != "time":
                self.operations.append((inst_id,op_id))
            else:
                self.operations.append((inst_id,op_id))

    def log_to_file(self):
        print(self.raw_dict.values())
        datafile = self.out_dir +self.rawfilename
        with open(datafile, "a") as outfile_raw:
            writer = csv.DictWriter(outfile_raw, fieldnames=self.op_names, lineterminator='\n', dialect="excel")
            writer.writerow(self.raw_dict)
        datafile = self.out_dir + self.transfilename
        with open(datafile, "a") as outfile_trans:
            writer = csv.DictWriter(outfile_trans, fieldnames=self.op_names, lineterminator='\n', dialect="excel")
            writer.writerow(self.trans_dict)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
        self.stopped = False

    def stop(self):
        self.stopped = True


class Timer(object):
    def __init__(self):
        self.start_time= time.time()

    def read_instrument(self,operation_id):
        op = getattr(self,operation_id)
        t = op()
        return t,t

    def reset_time(self):
        self.start_time = time.time()

    def runtime(self):
        return time.time() - self.start_time

    def datetime(self):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def main():
    pass

if __name__ == '__main__':
    main()